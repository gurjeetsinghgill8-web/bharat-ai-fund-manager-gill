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
        "LTIM.NS", "SHRIRAMFIN.NS", "BRITANNIA.NS", "TATACOMM.NS"
    ],
    "Mid Cap": [
        "PAGEIND.NS", "ESCORTS.NS", "CUMMINSIND.NS", "CONCOR.NS", "BHARATFORG.NS",
        "VOLTAS.NS", "RECLTD.NS", "PFC.NS", "TATAPOWER.NS", "CHOLAFIN.NS",
        "MRF.NS", "ASHOKLEY.NS", "MAXHEALTH.NS", "BALKRISIND.NS", "POLYCAB.NS",
        "BHEL.NS", "TRENT.NS", "BEL.NS", "HAL.NS", "GMRINFRA.NS", "COFORGE.NS",
        "PERSISTENT.NS", "DIXON.NS", "ASTRAL.NS", "AUROPHARMA.NS", "BANDHANBNK.NS",
        "FEDERALBNK.NS", "IDFCFIRSTB.NS", "JUBLFOOD.NS", "LICHSGFIN.NS", "L&TFH.NS",
        "NMDC.NS", "SAIL.NS", "TATAELXSI.NS", "YESBANK.NS", "IRFC.NS", "RVNL.NS",
        "OBEROIRLTY.NS", "PIIND.NS", "PETRONET.NS", "IPCALAB.NS", "IGL.NS"
    ],
    "Small Cap": [
        "CDSL.NS", "ANGELONE.NS", "BSE.NS", "HUDCO.NS", "IRCON.NS", "SJVN.NS",
        "SUZLON.NS", "NBCC.NS", "TRIDENT.NS", "ZENSARTECH.NS", "HFCL.NS",
        "IFCI.NS", "TATAINVEST.NS", "IEX.NS", "TATACHEM.NS", "RADICO.NS",
        "PNB.NS", "MCX.NS", "SIGNATURE.NS", "BECTORFOOD.NS", "ROUTE.NS",
        "HAPPYFORGE.NS", "MAPMYINDIA.NS", "SHYAMMETL.NS", "KARURVYSYA.NS", "RAMCOCEM.NS",
        "EASEMYTRIP.NS", "INFIBEAM.NS", "CENTURYTEX.NS", "NCC.NS", "IRCTC.NS",
        "NHPC.NS", "SWANENERGY.NS", "WELCORP.NS", "GPIL.NS", "PPLPHARMA.NS"
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

def get_all_tickers(use_full=False):
    """
    Returns a deduplicated list of ticker symbols with .NS suffix.
    
    Args:
        use_full: If True, returns ~2000+ NSE symbols (fetched from NSE archives).
                  If False, returns the 127 core watchlist (default).
    
    Returns:
        list of ticker strings (e.g., ["RELIANCE.NS", "TCS.NS", ...])
    """
    if use_full:
        # Get full NSE list (from cache/live/fallback)
        full = get_nse_tickers_with_suffix()
        # Ensure core stocks are always included
        core_set = set(get_all_tickers(use_full=False))
        full_set = set(full)
        combined = list(core_set | full_set)
        print(f"Full universe: {len(combined)} stocks (core={len(core_set)}, nse={len(full_set)})")
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
# Quick test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Core tickers: {len(get_all_tickers())}")
    print(f"Full NSE tickers: {len(get_all_tickers(use_full=True))}")
    print(f"Category of RELIANCE.NS: {get_category('RELIANCE.NS')}")
    print(f"Category of UNKNOWN.NS: {get_category('UNKNOWN.NS')}")
