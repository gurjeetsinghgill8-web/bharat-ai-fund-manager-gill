import os
import time
import pickle
import datetime
import concurrent.futures
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv
from screeners_scraper import fetch_screener_data
try:
    from supabase_db import save_scan_cache, load_scan_cache, get_scan_meta
except ImportError:
    from db import save_scan_cache, load_scan_cache, get_scan_meta

load_dotenv()
CACHE_EXPIRY_DAYS = int(os.getenv("CACHE_EXPIRY_DAYS", "7"))
import tempfile

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

# Detect if the local repository directory is writeable
_is_writeable = False
try:
    _test_path = os.path.join(LOCAL_DIR, ".data_write_test")
    with open(_test_path, "w") as _f:
        _f.write("1")
    os.remove(_test_path)
    _is_writeable = True
except Exception:
    _is_writeable = False

if _is_writeable:
    CACHE_DIR = os.path.join(LOCAL_DIR, "data_cache")
else:
    CACHE_DIR = os.path.join(tempfile.gettempdir(), "data_cache")

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_path(ticker):
    safe_ticker = ticker.replace(".", "_")
    return os.path.join(CACHE_DIR, f"{safe_ticker}.pkl")

def is_cache_fresh(filepath):
    if not os.path.exists(filepath):
        return False
    
    file_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
    age = datetime.datetime.now() - file_time
    return age.days < CACHE_EXPIRY_DAYS

def fetch_stock_data(ticker, force_refresh=False):
    """
    Fetches raw stock data from yfinance and returns a structured dictionary.
    """
    try:
        t = yf.Ticker(ticker)
        
        # 1. Fetch Price History
        hist = t.history(period="max")
        if hist.empty:
            hist = t.history(period="5y")
            
        if hist.empty:
            return None

        current_price = float(hist['Close'].iloc[-1])
        ath = float(hist['Close'].max())
        
        # Calculate 3y High
        three_years_ago = datetime.datetime.now() - datetime.timedelta(days=3*365)
        hist_3y = hist.loc[hist.index >= pd.to_datetime(three_years_ago, utc=True)]
        if not hist_3y.empty:
            three_year_high = float(hist_3y['Close'].max())
        else:
            three_year_high = ath
            
        # Calculate 200 SMA
        sma_200 = 0.0
        if len(hist) >= 200:
            sma_200 = float(hist['Close'].rolling(window=200).mean().iloc[-1])
        elif not hist.empty:
            sma_200 = float(hist['Close'].mean())
            
        # 2. Fetch Sales & Profit History
        # PREFERRED: Screeners.in — provides 10+ years of clean financial data (needed for CAGR)
        # FALLBACK: yfinance financials — provides max ~4 years for Indian stocks (5Y CAGR fails)
        #
        # NOTE: Most Indian stocks have only 4 data points from yfinance, which is insufficient
        # for 5Y CAGR calculation (needs >= 5). Screeners.in provides 12 years.
        # The screener cache persists for 14 days, so repeated scans are instant.
        
        # Try screeners.in first for reliable CAGR data
        # Cache is checked internally — no network call if cached
        screener_result = fetch_screener_data(ticker, force_refresh=force_refresh)
        
        if screener_result["success"] and len(screener_result["sales"]) >= 5:
            sales_history = screener_result["sales"]
            profit_history = screener_result["profit"]
        else:
            # Fallback to yfinance
            financials = t.financials
            sales_history = []
            if financials is not None and not financials.empty:
                revenue_keys = [k for k in financials.index if 'Revenue' in k or 'Sales' in k or 'Operating Revenue' in k]
                if revenue_keys:
                    sales_history = financials.loc[revenue_keys[0]].dropna().tolist()
                    
            profit_history = []
            if financials is not None and not financials.empty:
                profit_keys = [k for k in financials.index if 'Net Income' in k or 'Profit' in k]
                if profit_keys:
                    profit_history = financials.loc[profit_keys[0]].dropna().tolist()
                
        # Extract Quarterly Profits (from yfinance — only needed for quarter_score)
        quarterly_financials = t.quarterly_financials
        quarterly_profits = []
        if quarterly_financials is not None and not quarterly_financials.empty:
            profit_keys = [k for k in quarterly_financials.index if 'Net Income' in k or 'Profit' in k]
            if profit_keys:
                quarterly_profits = quarterly_financials.loc[profit_keys[0]].dropna().tolist()

        # 3. Get Key Info (PE, EPS, Debt, Reserves, Shareholdings)
        info = t.info
        
        # Safe extraction of keys from info dict
        pe = info.get('trailingPE') or info.get('forwardPE') or 0.0
        eps = info.get('trailingEps') or info.get('forwardEps') or 0.0
        
        debt_to_equity = info.get('debtToEquity') or 0.0
        
        # Reserves
        reserves = 0.0
        balance_sheet = t.balance_sheet
        if balance_sheet is not None and not balance_sheet.empty:
            reserves_keys = [k for k in balance_sheet.index if 'Retained Earnings' in k or 'Surplus' in k or 'Reserves' in k]
            if reserves_keys:
                reserves_series = balance_sheet.loc[reserves_keys[0]].dropna()
                if not reserves_series.empty:
                    reserves = float(reserves_series.iloc[0])
                    
        # Total Borrowings/Debt
        debt = 0.0
        if balance_sheet is not None and not balance_sheet.empty:
            debt_keys = [k for k in balance_sheet.index if 'Long Term Debt' in k or 'Total Debt' in k or 'Borrowings' in k]
            if debt_keys:
                debt_series = balance_sheet.loc[debt_keys[0]].dropna()
                if not debt_series.empty:
                    debt = float(debt_series.iloc[0])

        # Shareholding details
        held_by_insiders = info.get('heldPercentInsiders') or 0.0
        held_by_institutions = info.get('heldPercentInstitutions') or 0.0
        
        promoter_share = held_by_insiders * 100.0 if held_by_insiders <= 1.0 else held_by_insiders
        inst_share = held_by_institutions * 100.0 if held_by_institutions <= 1.0 else held_by_institutions
        public_share = max(0.0, 100.0 - promoter_share - inst_share)

        # Market Cap & PEG Ratio
        market_cap = float(info.get('marketCap') or 0.0)
        market_cap_cr = round(market_cap / 10_000_000.0, 2)
        peg = info.get('pegRatio')
        peg_ratio = float(peg) if peg is not None and str(peg) != 'None' and float(peg) > 0 else 0.0

        # Sector, Industry, Exchange
        sector = info.get('sector', "Unknown")
        industry = info.get('industry', "Unknown")
        exchange = "NSE" if ".NS" in ticker else ("BSE" if ".BO" in ticker else "Unknown")

        data = {
            "ticker": ticker,
            "current_price": current_price,
            "ath": ath,
            "three_year_high": three_year_high,
            "sales_history": sales_history,
            "profit_history": profit_history,
            "quarterly_profits": quarterly_profits,
            "pe": pe,
            "eps": eps,
            "market_cap": market_cap,
            "market_cap_cr": market_cap_cr,
            "peg_ratio": peg_ratio,
            "debt_to_equity": debt_to_equity,
            "debt": debt,
            "reserves": reserves,
            "promoter_share": promoter_share,
            "inst_share": inst_share,
            "public_share": public_share,
            "price_history_6m": hist['Close'].tail(180).tolist() if len(hist) > 180 else hist['Close'].tolist(),
            "price_history_5y": hist['Close'].tail(5*252).tolist() if len(hist) > (5*252) else hist['Close'].tolist(),
            "sma_200": sma_200,
            "sector": sector,
            "industry": industry,
            "exchange": exchange,
            "timestamp": datetime.datetime.now(),
            "_cache_version": 4  # v4 = added market_cap_cr, peg_ratio
        }
        return data
    except Exception as e:
        print(f"Error fetching data for {ticker}: {str(e)}")
        return None

def get_stock_data(ticker, force_refresh=False):
    cache_path = get_cache_path(ticker)
    
    if not force_refresh and is_cache_fresh(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                cached = pickle.load(f)
            # Check cache version — v1 (yfinance only, <5 data points) needs refetch
            if cached.get("_cache_version", 1) < 2:
                print(f"{ticker}: Old cache format (v{cached.get('_cache_version', 1)}), refetching with screeners...")
                force_refresh = True
            # Also check if cached data has sufficient history for CAGR (>=5 data points)
            elif len(cached.get("sales_history", [])) < 5 or len(cached.get("profit_history", [])) < 5:
                print(f"{ticker}: Cache has insufficient history ({len(cached.get('sales_history', []))} sales pts), refetching...")
                force_refresh = True
            else:
                return cached
        except Exception:
            force_refresh = True
            
    # Fetch fresh data
    data = fetch_stock_data(ticker)
    if data:
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Error caching data for {ticker}: {str(e)}")
            
    return data

def batch_update_stocks(tickers, force_refresh=False, progress_callback=None):
    """
    Sequential batch fetch — one stock at a time with 0.1s sleep.
    Best for small lists (< 200 stocks).
    """
    results = {}
    total = len(tickers)
    for idx, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(idx, total, ticker)
        data = get_stock_data(ticker, force_refresh=force_refresh)
        if data:
            results[ticker] = data
        time.sleep(0.1)
    return results


def batch_update_stocks_parallel(tickers, force_refresh=False, max_workers=10, progress_callback=None):
    """
    Parallel batch fetch using ThreadPoolExecutor.
    Best for large lists (2000+ stocks) — ~30 seconds instead of ~3 minutes.
    
    Args:
        tickers: list of ticker symbols
        force_refresh: bypass cache if True
        max_workers: number of parallel threads (default 10)
        progress_callback: function(idx, total, ticker) for UI progress
    
    Returns:
        dict of {ticker: stock_data}
    """
    results = {}
    total = len(tickers)
    completed = [0]  # mutable counter for callback
    lock = [None]    # placeholder for thread safety (simplified)

    def fetch_one(ticker):
        data = get_stock_data(ticker, force_refresh=force_refresh)
        return (ticker, data)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_one, t): t for t in tickers}
        for future in concurrent.futures.as_completed(futures):
            ticker = futures[future]
            try:
                _, data = future.result()
                if data:
                    results[ticker] = data
            except Exception as e:
                print(f"Error fetching {ticker}: {e}")
            
            completed[0] += 1
            if progress_callback:
                progress_callback(completed[0], total, ticker)
    
    return results


# ---------------------------------------------------------------------------
# SCAN PERSISTENCE (SQLite layer)
# ---------------------------------------------------------------------------

def save_scan_results_to_db(results):
    """
    Saves scan results to SQLite for persistence across app restarts.
    Called after every scan (manual or automated).
    """
    try:
        save_scan_cache(results)
        print(f"✅ Scan results saved to SQLite ({len(results)} stocks)")
    except Exception as e:
        print(f"Error saving scan to DB: {e}")


def load_cached_scan_from_db():
    """
    Loads last scan results from SQLite.
    Called on app startup to avoid empty dashboard.
    Returns: {ticker: {data_dict}} or empty dict.
    """
    try:
        results = load_scan_cache()
        if results:
            meta = get_scan_meta()
            last_time = meta.get("last_scan_time", "Unknown")
            print(f"📦 Loaded {len(results)} stocks from SQLite cache (last scan: {last_time})")
        return results
    except Exception as e:
        print(f"Error loading scan from DB: {e}")
        return {}
