"""
NSE Tickers Module — Auto-fetch 2000+ NSE stock symbols (Lego Brick 1)

How it works:
1. Fetches fresh tickers from NSE archives CSV (~2071 EQ stocks)
2. Falls back to embedded static list if network fails
3. Caches tickers locally for 30 days to avoid repeated downloads
4. Returns symbols WITHOUT .NS suffix (caller adds it as needed)
"""

import os
import json
import datetime
import requests

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
NSE_CACHE_FILE = "nse_tickers_cache.json"
NSE_CACHE_EXPIRY_DAYS = 30
NSE_CSV_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

# ---------------------------------------------------------------------------
# Embedded static fallback (top ~300 actively traded NSE stocks)
# Used when network is unavailable
# ---------------------------------------------------------------------------
FALLBACK_TICKERS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "BHARTIARTL", "SBIN",
    "ITC", "HINDUNILVR", "LICI", "HCLTECH", "LT", "AXISBANK", "SUNPHARMA",
    "KOTAKBANK", "MARUTI", "COALINDIA", "NTPC", "ULTRACEMCO", "TITAN", "ONGC",
    "ASIANPAINT", "ADANIENT", "POWERGRID", "TATASTEEL", "BAJFINANCE", "BAJAJFINSV",
    "NESTLEIND", "JSWSTEEL", "M&M", "GRASIM", "TATACONSUM", "TECHM", "WIPRO",
    "CIPLA", "APOLLOHOSP", "HINDALCO", "SBILIFE", "DRREDDY", "ADANIPORTS", "BPCL",
    "EICHERMOT", "DIVISLAB", "HEROMOTOCO", "INDUSINDBK", "LTIM", "SHRIRAMFIN",
    "BRITANNIA", "TATACOMM", "PAGEIND", "ESCORTS", "CUMMINSIND", "CONCOR",
    "BHARATFORG", "VOLTAS", "RECLTD", "PFC", "TATAPOWER", "CHOLAFIN", "MRF",
    "ASHOKLEY", "MAXHEALTH", "BALKRISIND", "POLYCAB", "BHEL", "TRENT", "BEL",
    "HAL", "GMRAIRPORT", "COFORGE", "PERSISTENT", "DIXON", "ASTRAL", "AUROPHARMA",
    "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "JUBLFOOD", "LICHSGFIN", "NMDC",
    "SAIL", "TATAELXSI", "YESBANK", "IRFC", "RVNL", "OBEROIRLTY", "PIIND",
    "PETRONET", "IPCALAB", "IGL", "CDSL", "ANGELONE", "BSE", "HUDCO", "IRCON",
    "SJVN", "SUZLON", "NBCC", "TRIDENT", "ZENSARTECH", "HFCL", "IFCI", "IEX",
    "TATACHEM", "RADICO", "PNB", "MCX", "SIGNATURE", "IRCTC", "NHPC", "NCC",
    "EASEMYTRIP", "INFIBEAM", "CENTURYTEX", "RAMCOCEM", "KARURVYSYA", "GPIL",
    "WELCORP", "PPLPHARMA", "SWANENERGY", "MAPMYINDIA", "HAPPYFORGE", "BECTORFOOD",
    "ROUTE", "TATAINVEST", "SHYAMMETL", "MOTHERSON", "VEDL", "IOC", "GAIL",
    "HINDZINC", "BERGEPAINT", "DABUR", "MARICO", "COLPAL", "HAVELLS", "SIEMENS",
    "AMBUJACEM", "ACC", "ICICIPRULI", "HDFCLIFE", "DALBHARAT", "SHRIRAMFIN",
    "TVSMOTOR", "MUTHOOTFIN", "BIOCON", "LUPIN", "TORNTPHARM", "ALKEM",
    "ZYDUSLIFE", "ABB", "BOSCHLTD", "PIDILITIND", "WHIRLPOOL", "BLUESTARCO",
    "AARTIIND", "NAVINFLUOR", "DEEPAKNTR", "SRF", "CROMPTON", "VOLTAS",
    "AMBER", "VBL", "ZOMATO", "PAYTM", "POLICYBZR",
]


# ---------------------------------------------------------------------------
# Fetch live from NSE archives
# ---------------------------------------------------------------------------

def fetch_live_nse_tickers(include_all_series=False):
    """
    Downloads the NSE equity master CSV and extracts ticker symbols.
    If include_all_series=False (default): only EQ-series (actively traded) — ~2000 stocks.
    If include_all_series=True: includes all series (EQ, BE, BZ, etc.) — ~3000+ stocks.
    Returns a list of ticker symbols WITHOUT .NS suffix.
    Returns empty list on failure.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(NSE_CSV_URL, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"NSE CSV fetch failed: HTTP {r.status_code}")
            return []

        lines = r.text.strip().split("\n")
        if len(lines) < 2:
            print("NSE CSV too short (no data rows)")
            return []

        tickers = []
        for line in lines[1:]:  # Skip header
            parts = line.split(",")
            if len(parts) >= 3:
                series = parts[2].strip()
                if include_all_series:
                    # Include all series: EQ, BE, BZ, BT, etc.
                    tickers.append(parts[0].strip())
                elif series == "EQ":  # Series EQ = actively traded
                    tickers.append(parts[0].strip())

        print(f"NSE live fetch: {len(tickers)} symbols (include_all={include_all_series})")
        return tickers

    except requests.exceptions.ConnectionError:
        print("NSE CSV fetch: network unavailable")
        return []
    except Exception as e:
        print(f"NSE CSV fetch error: {e}")
        return []


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def load_cached_tickers():
    """Returns cached ticker list, or None if cache is missing/expired."""
    if not os.path.exists(NSE_CACHE_FILE):
        return None
    try:
        with open(NSE_CACHE_FILE, "r") as f:
            data = json.load(f)
        fetched = datetime.datetime.fromisoformat(data["fetched"])
        age = datetime.datetime.now() - fetched
        if age.days < NSE_CACHE_EXPIRY_DAYS:
            return data["tickers"]
        return None
    except Exception:
        return None


def save_cached_tickers(tickers):
    """Saves ticker list with timestamp."""
    try:
        data = {
            "fetched": datetime.datetime.now().isoformat(),
            "count": len(tickers),
            "tickers": tickers,
        }
        with open(NSE_CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving NSE cache: {e}")
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_nse_tickers(force_refresh=False, include_all_series=False):
    """
    Main function: returns the full list of NSE tickers (WITHOUT .NS suffix).
    
    Priority:
    1. Check local cache (if fresh)
    2. Fetch live from NSE (and cache)
    3. Fallback to embedded static list
    
    Args:
        force_refresh: If True, skip cache and fetch live
        include_all_series: If True, fetch all series (~3000+ stocks instead of ~2000 EQ-only)
    
    Returns:
        list of ticker symbols (e.g., ["RELIANCE", "TCS", ...])
    """
    # 1. Try cache first (unless forced refresh)
    if not force_refresh:
        cached = load_cached_tickers()
        if cached is not None:
            print(f"Using cached NSE tickers: {len(cached)} symbols")
            return cached

    # 2. Fetch live
    live = fetch_live_nse_tickers(include_all_series=include_all_series)
    if live:
        save_cached_tickers(live)
        return live

    # 3. Fallback to static list
    print(f"Using fallback tickers: {len(FALLBACK_TICKERS)} symbols")
    return list(FALLBACK_TICKERS)


def get_nse_tickers_with_suffix(force_refresh=False, include_all_series=False):
    """
    Same as get_nse_tickers() but appends .NS suffix for Yahoo Finance.
    """
    tickers = get_nse_tickers(force_refresh=force_refresh, include_all_series=include_all_series)
    return [f"{t}.NS" for t in tickers]


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    t = get_nse_tickers()
    print(f"\nTotal: {len(t)} tickers")
    print(f"First 10: {t[:10]}")
    print(f"Last 10:  {t[-10:]}")
