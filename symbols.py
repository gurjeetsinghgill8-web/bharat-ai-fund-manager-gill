"""
Stock Symbols for Bharat AI Fund Manager Gill (Lego Brick 2)

Dual-mode system:
  - CORE STOCKS: 127 manually curated stocks (Large/Mid/Small Cap)
  - FULL NSE: ~2000+ EQ-series stocks auto-fetched from NSE

Usage:
    get_all_tickers()              → returns 127 core tickers with .NS
    get_all_tickers(use_full=True) → returns 2000+ tickers with .NS
    get_category(ticker)           → returns cap category for any ticker
"""

from nse_tickers import get_nse_tickers, get_nse_tickers_with_suffix

# ---------------------------------------------------------------------------
# Core Watchlist — 127 hand-picked Indian stocks
# ---------------------------------------------------------------------------
CORE_STOCKS = {
    "Large Cap": [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "BHARTIARTL.NS", "SBIN.NS", "ITC.NS", "HINDUNILVR.NS", "LICI.NS",
        "HCLTECH.NS", "LT.NS", "AXISBANK.NS", "SUNPHARMA.NS", "KOTAKBANK.NS",
        "MARUTI.NS", "COALINDIA.NS", "NTPC.NS", "ULTRACEMCO.NS", "TITAN.NS",
        "ONGC.NS", "ASIANPAINT.NS", "ADANIENT.NS", "POWERGRID.NS", "TATASTEEL.NS",
        "BAJFINANCE.NS", "BAJAJFINSV.NS", "NESTLEIND.NS", "JSWSTEEL.NS", "M&M.NS",
        "GRASIM.NS", "TATACONSUM.NS", "TECHM.NS", "WIPRO.NS", "CIPLA.NS",
        "APOLLOHOSP.NS", "HINDALCO.NS", "SBILIFE.NS", "DRREDDY.NS", "ADANIPORTS.NS",
        "BPCL.NS", "EICHERMOT.NS", "DIVISLAB.NS", "HEROMOTOCO.NS", "INDUSINDBK.NS",
        "LTIMINDTECH.NS", "SHRIRAMFIN.NS", "BRITANNIA.NS", "TATACOMM.NS"
    ],
    "Mid Cap": [
        "PAGEIND.NS", "ESCORTS.NS", "CUMMINSIND.NS", "CONCOR.NS", "BHARATFORG.NS",
        "VOLTAS.NS", "RECLTD.NS", "PFC.NS", "TATAPOWER.NS", "CHOLAFIN.NS",
        "MRF.NS", "ASHOKLEY.NS", "MAXHEALTH.NS", "BALKRISIND.NS", "POLYCAB.NS",
        "BHEL.NS", "TRENT.NS", "BEL.NS", "HAL.NS", "JIOFIN.NS", "COFORGE.NS",
        "PERSISTENT.NS", "DIXON.NS", "ASTRAL.NS", "AUROPHARMA.NS", "BANDHANBNK.NS",
        "FEDERALBNK.NS", "IDFCFIRSTB.NS", "JUBLFOOD.NS", "LICHSGFIN.NS", "LTF.NS",
        "NMDC.NS", "SAIL.NS", "TATAELXSI.NS", "YESBANK.NS", "IRFC.NS", "RVNL.NS",
        "OBEROIRLTY.NS", "PIIND.NS", "PETRONET.NS", "IPCALAB.NS", "IGL.NS",
        "LUPIN.NS", "WAAREEENER.NS", "KALYANKJIL.NS", "MUTHOOTFIN.NS", "KPIL.NS"
    ],
    "Small Cap": [
        "CDSL.NS", "ANGELONE.NS", "BSE.NS", "HUDCO.NS", "IRCON.NS", "SJVN.NS",
        "SUZLON.NS", "NBCC.NS", "TRIDENT.NS", "ZENSARTECH.NS", "HFCL.NS",
        "IFCI.NS", "TATAINVEST.NS", "IEX.NS", "TATACHEM.NS", "RADICO.NS",
        "PNB.NS", "MCX.NS", "SIGNATURE.NS", "BECTORFOOD.NS", "ROUTE.NS",
        "HAPPYFORGE.NS", "MAPMYINDIA.NS", "SHYAMMETL.NS", "KARURVYSYA.NS", "RAMCOCEM.NS",
        "EASEMYTRIP.NS", "PSPPROJECT.NS", "CENTURYPLY.NS", "NCC.NS", "IRCTC.NS",
        "NHPC.NS", "KPIGREEN.NS", "WELCORP.NS", "GPIL.NS", "PPLPHARMA.NS",
        "SENCO.NS", "PNGJL.NS", "POWERINDIA.NS", "CCAVENUE.NS", "GRSE.NS",
        "SARDAEN.NS", "SKIPPER.NS", "PRECWIRE.NS", "RAMRAT.NS", "GENUSPOWER.NS",
        "DPABHUSHAN.NS", "PRICOL.NS", "BANCOINDIA.NS", "KAYNES.NS", "WAAREERTL.NS", "HBLPOWER.NS"
    ]
}

# Flattened lookup: symbol -> cap category
_CORE_LOOKUP = {}
for cap, tickers in CORE_STOCKS.items():
    for t in tickers:
        _CORE_LOOKUP[t] = cap


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_tickers(use_full=False, limit=None, include_bse=False):
    """
    Returns a deduplicated list of ticker symbols with .NS suffix (and optionally .BO).
    
    Args:
        use_full: If True, returns ~2000+ NSE symbols (fetched from NSE archives).
                  If False, returns the 127 core watchlist (default).
        limit: Optional int to limit total stocks returned (e.g., 50, 100, 500, 1000, 2000).
               Applied AFTER combining core + NSE sets.
        include_bse: If True, also returns BSE (.BO) tickers alongside NSE ones.
    
    Returns:
        list of ticker strings (e.g., ["RELIANCE.NS", "TCS.NS", ..., "RELIANCE.BO", ...])
    """
    if use_full:
        # Get full NSE list (from cache/live/fallback)
        # For limits > 2000, include all series to get ~3000+ stocks
        include_all = limit is not None and limit > 2000
        full = get_nse_tickers_with_suffix(include_all_series=include_all)
        # Ensure core stocks are always included
        core_set = set(get_all_tickers(use_full=False))
        full_set = set(full)
        combined = list(core_set | full_set)
        
        # Add BSE tickers if requested
        if include_bse:
            bse_set = set(get_bse_tickers())
            combined = list(set(combined) | bse_set)
            print(f"Full universe + BSE: {len(combined)} stocks")
        else:
            print(f"Full universe: {len(combined)} stocks (core={len(core_set)}, nse={len(full_set)})")
        
        # Apply limit if specified
        if limit is not None and limit > 0:
            # Keep core stocks first, then fill with NSE stocks up to limit
            core_list = list(core_set)
            nse_only = [t for t in combined if t not in core_set]
            limited = core_list + nse_only[:max(0, limit - len(core_list))]
            print(f"Limited universe: {len(limited)} stocks (limit={limit})")
            return limited
        
        return combined
    
    # Core watchlist
    all_tickers = []
    for cap, tickers in CORE_STOCKS.items():
        all_tickers.extend(tickers)
    return list(set(all_tickers))


def get_category(ticker):
    """
    Returns the market-cap category for a ticker.
    
    Priority:
    1. Check core watchlist lookup
    2. If full NSE mode, return "Universe" as default
    
    Returns:
        "Large Cap", "Mid Cap", "Small Cap", or "Universe"
    """
    if ticker in _CORE_LOOKUP:
        return _CORE_LOOKUP[ticker]
    return "Universe"


def get_all_categories(use_full=False):
    """
    Returns list of all available categories for UI filters.
    """
    if use_full:
        return ["All Stocks", "Large Cap", "Mid Cap", "Small Cap", "Universe"]
    return ["All Stocks", "Large Cap", "Mid Cap", "Small Cap"]


def get_core_stocks_list():
    """
    Returns the flat list of 127 core tickers (for reference).
    """
    return list(set(t for cap_list in CORE_STOCKS.values() for t in cap_list))


# ---------------------------------------------------------------------------
# BSE Ticker Support
# ---------------------------------------------------------------------------
def get_bse_tickers():
    """
    Returns BSE (.BO) ticker symbols derived from NSE EQ list.
    Most stocks listed on NSE are also listed on BSE with the same symbol.
    Returns list like ["RELIANCE.BO", "TCS.BO", ...]
    """
    from nse_tickers import get_nse_tickers
    nse_tickers = get_nse_tickers()  # Without .NS suffix
    return [f"{t}.BO" for t in nse_tickers]


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Core tickers: {len(get_all_tickers())}")
    print(f"Full NSE tickers: {len(get_all_tickers(use_full=True))}")
    print(f"Category of RELIANCE.NS: {get_category('RELIANCE.NS')}")
    print(f"Category of UNKNOWN.NS: {get_category('UNKNOWN.NS')}")
