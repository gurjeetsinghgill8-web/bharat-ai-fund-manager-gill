"""
screeners_scraper.py — Fetch 10+ years of Sales & Net Profit data from screener.in

Why: yfinance only returns 4 years of annual financial data for Indian stocks,
which makes 5Y CAGR calculation unreliable (needs >= 5 data points). Screener.in
provides 12 years (Mar 2015 – Mar 2026) of clean fiscal-year data.

Usage:
    from screeners_scraper import fetch_screener_data
    data = fetch_screener_data("AUROPHARMA")
    # Returns {"sales": [...], "profit": [...], "source": "...", "years": [...]}
    
    # Or with ticker including .NS:
    data = fetch_screener_data("AUROPHARMA.NS")
"""

import os
import json
import time
import datetime
import re
import requests
from bs4 import BeautifulSoup

# Cache settings
import tempfile

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

# Detect if the local repository directory is writeable
_is_writeable = False
try:
    _test_path = os.path.join(LOCAL_DIR, ".screener_write_test")
    with open(_test_path, "w") as _f:
        _f.write("1")
    os.remove(_test_path)
    _is_writeable = True
except Exception:
    _is_writeable = False

if _is_writeable:
    SCREENER_CACHE_DIR = os.path.join(LOCAL_DIR, "screener_cache")
else:
    SCREENER_CACHE_DIR = os.path.join(tempfile.gettempdir(), "screener_cache")

SCREENER_CACHE_DAYS = 14  # Re-check every 14 days

if not os.path.exists(SCREENER_CACHE_DIR):
    os.makedirs(SCREENER_CACHE_DIR)

_LAST_REQUEST_TIME = 0
_MIN_REQUEST_INTERVAL = 1.0  # 1 second between requests to be polite

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _get_screener_symbol(ticker):
    """Convert yahoo ticker (AUROPHARMA.NS) to screener.in symbol (AUROPHARMA)."""
    s = ticker.strip().upper()
    if s.endswith(".NS"):
        s = s[:-3]
    return s


def _get_cache_path(symbol):
    """Return cache file path for a given screener symbol."""
    safe = symbol.replace(".", "_").replace("/", "_")
    return os.path.join(SCREENER_CACHE_DIR, f"{safe}.json")


def _is_cache_fresh(filepath):
    """Check if cache file is still fresh based on SCREENER_CACHE_DAYS."""
    if not os.path.exists(filepath):
        return False
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
    age = datetime.datetime.now() - mtime
    return age.days < SCREENER_CACHE_DAYS


def _save_cache(symbol, data):
    """Save scraped data to cache file."""
    cache_path = _get_cache_path(symbol)
    try:
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"screener_cache: write error for {symbol}: {e}")


def _load_cache(symbol, require_balance_sheet=False):
    """Load cached data if fresh, else return None.

    `require_balance_sheet` re-fetches a cache written before `cache_version` 2, which is what
    a bank / NBFC needs (that version added Equity Capital, Reserves, Deposits, Borrowing and
    Total Assets). data_fetcher asks for it only for records it classifies as lenders, so
    upgrading does not force a 1,682-stock refetch.
    """
    cache_path = _get_cache_path(symbol)
    if _is_cache_fresh(cache_path):
        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)
            if require_balance_sheet and cached.get("cache_version", 1) < 2:
                return None
            return cached
        except Exception:
            pass
    return None


def _parse_indian_number(text):
    """
    Parse Indian-format number string to float.
    
    Handles:
        "1,23,456" → 123456
        "1,23,456.78" → 123456.78
        "1,234.5" → 1234.5
        "-" → 0.0
        "0" → 0.0
    """
    if not text or text.strip() in ("", "-", "--"):
        return 0.0
    
    s = text.strip()
    # Remove ₹ symbol or other currency indicators
    s = s.replace("₹", "").replace("$", "").replace("€", "").strip()
    
    # Remove all commas first, then parse
    s = s.replace(",", "")
    
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_crores_to_absolute(value_in_crores):
    """
    Screener.in shows values in crores (1 crore = 10,000,000).
    Convert to absolute Rupee value for yfinance compatibility.
    """
    return value_in_crores * 10_000_000


def _parse_pct(text):
    """'23%' → 23.0, '-16%' → -16.0, '' / '-' → None (a real 0% is preserved)."""
    if text is None:
        return None
    s = str(text).strip().replace(",", "").replace("₹", "")
    if s in ("", "-", "--", "N/A"):
        return None
    s = s.rstrip("%").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _row_label(text):
    """Normalise a Screener.in row label: 'Revenue +' → 'revenue', 'Total Assets' → 'total assets'.

    Screener.in appends a '+' to the first row of each block and pads labels with
    non-breaking spaces, so matching on the raw string is brittle.
    """
    s = str(text or "").replace("\u00a0", " ").replace("+", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def _last_value(cells):
    """The right-most non-empty cell — Screener.in prints oldest → latest, left → right."""
    for c in reversed(cells):
        if c is not None and str(c).strip() not in ("", "-", "--"):
            return c
    return None


def _extract_balance_sheet_block(soup):
    """
    Pull the latest balance-sheet figures off a screener.in company page.

    Why this matters for lenders: a bank/NBFC is not judged on ROCE or Debt/Equity < 0.5 — it
    is judged on return on assets, the capital cushion (net worth ÷ total assets) and asset
    quality. yfinance gives us none of that for an Indian lender, but screener.in prints the
    full balance sheet (Equity Capital, Reserves, Deposits, Borrowing, Total Assets) and the
    P&L "Financing Margin %" FOR FREE, without a login.

    Bonus for everybody else: `net_worth_cr` = Equity Capital + Reserves is the REAL
    shareholder equity. The yfinance "Reserves" field that lynch_engine previously used as an
    equity proxy is actually *retained earnings*, which understates equity for every company
    that has issued share capital — so ROE estimates get better here too, not just for banks.

    Gross NPA % / Net NPA % / Capital Adequacy Ratio also appear as ROWS on a lender page, but
    Screener.in BLANKS THEIR VALUES behind a login wall — so they are deliberately NOT scraped.
    We never guess an NPA; the score card takes it as a manual entry instead.

    Returns None when the page carries no balance-sheet rows at all.
    """
    # ── P&L side: Financing Margin % (the lender's margin / NIM proxy) ──
    financing_margin = None
    financing_profit_cr = None
    for sec in soup.find_all("section"):
        h2 = sec.find("h2")
        if not h2 or "Profit" not in h2.get_text(strip=True):
            continue
        table = sec.find("table")
        if table is None:
            continue
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) < 2:
                continue
            label = _row_label(cells[0])
            if label == "financing margin %":
                financing_margin = _parse_pct(_last_value(cells[1:]))
            elif label == "financing profit":
                financing_profit_cr = _parse_indian_number(_last_value(cells[1:]) or "")
        break

    # ── Balance sheet side ──
    bs = {}
    for sec in soup.find_all("section"):
        h2 = sec.find("h2")
        if not h2 or "Balance Sheet" not in h2.get_text(strip=True):
            continue
        table = sec.find("table")
        if table is None:
            continue
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if len(cells) < 2:
                continue
            label = _row_label(cells[0])
            raw = _last_value(cells[1:])
            if label in ("equity capital", "reserves", "deposits", "borrowing", "borrowings",
                         "total assets", "total liabilities"):
                bs[label] = _parse_indian_number(raw) if raw is not None else 0.0
        break

    equity_capital = bs.get("equity capital")
    reserves = bs.get("reserves")
    if equity_capital is None and reserves is None:
        return None                      # no balance sheet on the page

    net_worth = (equity_capital or 0.0) + (reserves or 0.0)

    return {
        "net_worth_cr": round(net_worth, 2) if net_worth else None,
        "equity_capital_cr": equity_capital,
        "reserves_cr": reserves,
        "borrowings_cr": bs.get("borrowing", bs.get("borrowings")),
        "deposits_cr": bs.get("deposits"),
        "total_assets_cr": bs.get("total assets"),
        "total_liabilities_cr": bs.get("total liabilities"),
        "financing_margin_pct": financing_margin,
        "financing_profit_cr": financing_profit_cr,
    }


def fetch_screener_data(ticker, force_refresh=False, require_balance_sheet=False):
    """
    Fetch 10+ years of Sales & Net Profit from screener.in

    Args:
        ticker: str — "AUROPHARMA.NS" or "AUROPHARMA"
        force_refresh: bool — bypass cache if True
        require_balance_sheet: bool — ignore a cache written before `cache_version` 2 (no
            Equity Capital / Reserves / Deposits / Borrowing / Total Assets). Pass True for
            banks & NBFCs, whose scoring needs the balance sheet.

    Returns:
        dict with keys:
            - "sales": list of annual sales values (absolute, latest first), or []
            - "profit": list of annual profit values (absolute, latest first), or []
            - "years": list of year labels (latest first), or []
            - "source": str — "screener.in" or "yfinance_fallback"
            - "success": bool
            - "balance_sheet": dict of ₹ Cr figures (or None), incl. "net_worth_cr" and
              "financing_margin_pct"
    
    Usage:
        result = fetch_screener_data("AUROPHARMA.NS")
        if result["success"]:
            sales_hist = result["sales"]     # [latest, ..., oldest]
            profit_hist = result["profit"]   # [latest, ..., oldest]
    """
    global _LAST_REQUEST_TIME
    
    symbol = _get_screener_symbol(ticker)
    
    # Check cache first
    if not force_refresh:
        cached = _load_cache(symbol, require_balance_sheet=require_balance_sheet)
        if cached is not None:
            return cached
    
    # Rate-limit requests to screener.in
    now = time.time()
    since_last = now - _LAST_REQUEST_TIME
    if since_last < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - since_last)
    
    # Try consolidated URL first (matching Screener.in default screen engine)
    url_cons = f"https://www.screener.in/company/{symbol}/consolidated/"
    url_standalone = f"https://www.screener.in/company/{symbol}/"
    
    try:
        resp = requests.get(url_cons, headers=HEADERS, timeout=20)
        _LAST_REQUEST_TIME = time.time()
        
        # Check if consolidated URL worked and has P&L table
        is_valid_cons = False
        if resp.status_code == 200:
            soup_test = BeautifulSoup(resp.text, "html.parser")
            for s in soup_test.find_all("section"):
                h2 = s.find("h2")
                if h2 and "Profit" in h2.get_text(strip=True) and s.find("table"):
                    is_valid_cons = True
                    break
        
        if not is_valid_cons:
            # Fall back to standalone URL
            resp = requests.get(url_standalone, headers=HEADERS, timeout=20)
            _LAST_REQUEST_TIME = time.time()
            if resp.status_code != 200:
                print(f"screener_scraper: HTTP {resp.status_code} for {symbol}")
                return {"sales": [], "profit": [], "years": [], "source": "screener.in", "success": False}
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Find the "Profit & Loss" section
        sections = soup.find_all("section")
        pl_section = None
        for s in sections:
            h2 = s.find("h2")
            if h2 and "Profit" in h2.get_text(strip=True):
                pl_section = s
                break
        
        if pl_section is None:
            print(f"screener_scraper: No Profit & Loss section found for {symbol}")
            return {"sales": [], "profit": [], "years": [], "source": "screener.in", "success": False}
        
        table = pl_section.find("table")
        if table is None:
            print(f"screener_scraper: No table in P&L section for {symbol}")
            return {"sales": [], "profit": [], "years": [], "source": "screener.in", "success": False}
        
        rows = table.find_all("tr")
        
        # Extract column headers (year labels)
        years = []
        sales_raw = []
        profit_raw = []
        
        for row in rows:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            
            text_cells = [c.get_text(strip=True) for c in cells]
            first_col = text_cells[0] if text_cells else ""
            
            # --- HEADER ROW (years) ---
            # The header row has first cell empty, and subsequent cells like "Mar 2015", "Mar 2016", ...
            # Check if ANY cell contains "Mar" or any year pattern (except possibly the first)
            header_text = " ".join(text_cells)
            if re.search(r'\bMar 20\d{2}\b', header_text) and len(text_cells) > 5:
                years = text_cells[1:]  # skip the empty first " " header label
                continue
            
            # --- SALES / REVENUE ROW ---
            # Non-banks: "Sales +"
            # Banks: "Revenue +"
            if "Sales" in first_col or first_col == "Revenue +":
                sales_raw = text_cells[1:]
                continue
            
            # --- NET PROFIT ROW ---
            if "Net Profit" in first_col:
                profit_raw = text_cells[1:]
                continue
        
        # If we didn't find Sales, try "Revenue +" for banks
        if not sales_raw:
            for row in rows:
                cells = row.find_all(["th", "td"])
                if not cells:
                    continue
                text_cells = [c.get_text(strip=True) for c in cells]
                first_col = text_cells[0] if text_cells else ""
                if "Revenue" in first_col or "Total Income" in first_col:
                    sales_raw = text_cells[1:]
                    break
        
        if not years:
            print(f"screener_scraper: No year headers found for {symbol}")
            return {"sales": [], "profit": [], "years": [], "source": "screener.in", "success": False}
        
        # Clean empty sales/profit — trim trailing empty cells
        def _trim_trailing_empty(vals):
            while vals and (not vals[-1] or vals[-1].strip() in ("", "-")):
                vals = vals[:-1]
            return vals
        
        sales_raw = _trim_trailing_empty(sales_raw)
        profit_raw = _trim_trailing_empty(profit_raw)

        # ── DROP NON-FISCAL-YEAR COLUMNS (the "TTM" column) ─────────────────────
        # Once a new quarter is published, Screener.in prepends a rolling-twelve-month "TTM"
        # column: [TTM, Mar 2026, Mar 2025, ...]. A TTM figure is NOT a fiscal year, so leaving
        # it in the series shifts every CAGR window forward by one year AND turns the latest
        # growth into TTM ÷ full-year — for CHOLAFIN that reported 5% growth instead of 20%.
        # Keep the TTM numbers aside as `sales_ttm` / `profit_ttm`; score only full years.
        fiscal_idx = [i for i, y in enumerate(years) if re.match(r"\s*Mar\s+\d{4}\s*$", str(y))]
        sales_ttm_cr = profit_ttm_cr = None
        if fiscal_idx and len(fiscal_idx) < len(years):
            extra_idx = [i for i in range(len(years)) if i not in fiscal_idx]
            # The rolling column sits at the right-hand (newest) end of the table.
            for i in extra_idx:
                if i < len(sales_raw) and sales_ttm_cr is None:
                    sales_ttm_cr = _parse_indian_number(sales_raw[i])
                if i < len(profit_raw) and profit_ttm_cr is None:
                    profit_ttm_cr = _parse_indian_number(profit_raw[i])
            years = [years[i] for i in fiscal_idx]
            sales_raw = [sales_raw[i] for i in fiscal_idx if i < len(sales_raw)]
            profit_raw = [profit_raw[i] for i in fiscal_idx if i < len(profit_raw)]
        
        # Match years to data length
        def _align_years(y, raw):
            """Trim years list to match data length (from right, oldest first)."""
            if len(raw) < len(y):
                return y[-len(raw):]
            return y
        
        aligned_years = _align_years(years, sales_raw)
        
        # Parse numbers (convert crores → absolute)
        sales_abs = [_parse_crores_to_absolute(_parse_indian_number(v)) for v in sales_raw]
        profit_abs = [_parse_crores_to_absolute(_parse_indian_number(v)) for v in profit_raw]
        
        # Ensure profit list matches length of sales
        if len(profit_abs) < len(sales_abs):
            profit_abs = [_parse_crores_to_absolute(_parse_indian_number(v)) for v in profit_raw[:len(sales_abs)]]
        
        # Reverse so that latest is first (index 0 = most recent COMPLETE fiscal year)
        # Screener.in shows oldest on left, latest on right
        sales_abs.reverse()
        profit_abs.reverse()
        aligned_years.reverse()

        # Full balance sheet (net worth, borrowings, deposits, total assets) + the lender
        # "Financing Margin %". None when the page has no balance-sheet rows. See
        # _extract_balance_sheet_block(). Whether a stock IS a lender is decided later from
        # sector/industry — never from the shape of the balance sheet.
        balance_sheet = _extract_balance_sheet_block(soup)

        result = {
            "sales": sales_abs,
            "profit": profit_abs,
            "years": aligned_years,
            # Rolling-twelve-month figures kept aside, NOT scored: they are not a fiscal year.
            "sales_ttm": _parse_crores_to_absolute(sales_ttm_cr) if sales_ttm_cr else None,
            "profit_ttm": _parse_crores_to_absolute(profit_ttm_cr) if profit_ttm_cr else None,
            "source": "screener.in",
            "success": True,
            "fetched_at": datetime.datetime.now().isoformat(),
            # v2 = adds the balance-sheet block (net worth / borrowings / deposits / total
            # assets / financing margin). data_fetcher treats a v1 cache as stale only for
            # records it classifies as lenders, so a rescan refreshes the ~120 banks & NBFCs
            # without forcing a 1,682-stock refetch.
            "cache_version": 2,
            "balance_sheet": balance_sheet,
        }
        
        # Cache the result
        _save_cache(symbol, result)
        
        return result
    
    except requests.exceptions.Timeout:
        print(f"screener_scraper: Timeout fetching {symbol}")
        return {"sales": [], "profit": [], "years": [], "source": "screener.in", "success": False}
    except requests.exceptions.ConnectionError:
        print(f"screener_scraper: Connection error for {symbol}")
        return {"sales": [], "profit": [], "years": [], "source": "screener.in", "success": False}
    except Exception as e:
        print(f"screener_scraper: Error for {symbol}: {e}")
        return {"sales": [], "profit": [], "years": [], "source": "screener.in", "success": False}


def clear_cache(symbol=None):
    """Clear screener.in cache for one symbol or all."""
    if symbol:
        sym = _get_screener_symbol(symbol)
        path = _get_cache_path(sym)
        if os.path.exists(path):
            os.remove(path)
        return
    # Clear all
    if os.path.exists(SCREENER_CACHE_DIR):
        for f in os.listdir(SCREENER_CACHE_DIR):
            if f.endswith(".json"):
                os.remove(os.path.join(SCREENER_CACHE_DIR, f))


if __name__ == "__main__":
    # Quick test
    import sys
    
    test_ticker = sys.argv[1] if len(sys.argv) > 1 else "AUROPHARMA.NS"
    print(f"Testing screeners scraper for {test_ticker}...")
    
    result = fetch_screener_data(test_ticker, force_refresh=True)
    
    if result["success"]:
        print(f"Source: {result['source']}")
        print(f"Years ({len(result['years'])}): {result['years']}")
        print(f"Sales ({len(result['sales'])}): {[f'{v:.0f}' for v in result['sales'][:6]]}...")
        print(f"Profit ({len(result['profit'])}): {[f'{v:.0f}' for v in result['profit'][:6]]}...")
        
        # Demo CAGR calculation
        from scoring_engine import calculate_cagr, calculate_cagr_for_years
        
        sales = result["sales"]
        profit = result["profit"]
        
        if len(sales) >= 6:
            cagr_3y = calculate_cagr_for_years(sales, 3)   # true 3-year CAGR
            cagr_5y = calculate_cagr_for_years(sales, 5)   # true 5-year CAGR
            cagr_all = calculate_cagr(sales)
            print(f"\nSales CAGR All: {cagr_all:.2f}%" if cagr_all else "Sales CAGR All: N/A")
            print(f"Sales CAGR 3Y:  {cagr_3y:.2f}%" if cagr_3y else "Sales CAGR 3Y: N/A")
            print(f"Sales CAGR 5Y:  {cagr_5y:.2f}%" if cagr_5y else "Sales CAGR 5Y: N/A")
        
        if len(profit) >= 6:
            pcagr_3y = calculate_cagr_for_years(profit, 3)  # true 3-year CAGR
            pcagr_5y = calculate_cagr_for_years(profit, 5)  # true 5-year CAGR
            pcagr_all = calculate_cagr(profit)
            print(f"\nProfit CAGR All: {pcagr_all:.2f}%" if pcagr_all else "Profit CAGR All: N/A")
            print(f"Profit CAGR 3Y:  {pcagr_3y:.2f}%" if pcagr_3y else "Profit CAGR 3Y: N/A")
            print(f"Profit CAGR 5Y:  {pcagr_5y:.2f}%" if pcagr_5y else "Profit CAGR 5Y: N/A")
    else:
        print(f"Failed to fetch data for {test_ticker}")
