# api/index.py — Vercel Serverless Entrypoint for Bharat AI Fund Manager Gill
import os
import sys
import asyncio
import datetime
import traceback
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure local api/ directory is on sys.path
_API_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_API_DIR)
for p in [_API_DIR, _ROOT_DIR, "/var/task/api", "/var/task"]:
    if p and os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

load_dotenv(os.path.join(_ROOT_DIR, ".env"))

# ── Project imports ────────────────────────────────────────────────────────────
try:
    import supabase_db as db
    from symbols import get_all_tickers
    from llm_harness import generate_ai_narrative, has_active_api_key
except ImportError:
    from api import supabase_db as db
    from api.symbols import get_all_tickers
    from api.llm_harness import generate_ai_narrative, has_active_api_key

API_SECRET = os.getenv("FASTAPI_SECRET_KEY", "bharat-ai-secret-2026")
_scan_running = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("  BHARAT AI FUND MANAGER — Vercel Serverless API Starting")
    print("=" * 60)
    try:
        db.init_db()
    except Exception as e:
        print(f"Supabase warning on startup: {e}")
    yield
    print("Vercel Serverless API shutting down.")

app = FastAPI(
    title="Bharat AI Fund Manager Gill API",
    description="Vercel Serverless Backend API",
    version="2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if API_SECRET and API_SECRET != "bharat-ai-secret-2026":
        if x_api_key != API_SECRET:
            raise HTTPException(status_code=401, detail="Invalid API key")

# Pydantic Request Models
class UserCreate(BaseModel):
    name: str
    email: Optional[str] = None

class HoldingAdd(BaseModel):
    user_id: int = 1
    symbol: str
    buy_price: float
    quantity: float
    buy_date: Optional[str] = None

class StockAsk(BaseModel):
    symbol: str
    user_id: int = 1

# Endpoints
@app.get("/")
@app.get("/health")
@app.get("/api/health")
def health_check():
    supabase_ok = False
    try:
        db.init_db()
        supabase_ok = True
    except Exception:
        pass
    meta = db.get_scan_meta() if supabase_ok else {}
    return {
        "status": "healthy",
        "supabase": "connected" if supabase_ok else "disconnected",
        "last_scan": meta.get("last_scan_time"),
        "total_stocks_scanned": meta.get("total_stocks", 0),
        "server_time": datetime.datetime.now().isoformat(),
        "version": "2.0"
    }

@app.get("/wake")
@app.get("/api/wake")
def wake_up():
    db.init_db()
    meta = db.get_scan_meta()
    return {
        "status": "awake",
        "timestamp": datetime.datetime.now().isoformat(),
        "last_scan": meta.get("last_scan_time"),
        "total_stocks": meta.get("total_stocks", 0),
    }

def _run_scan_job(universe_size: int = 0):
    global _scan_running
    if _scan_running:
        return
    _scan_running = True
    try:
        try:
            from data_fetcher import batch_update_stocks_parallel, batch_update_stocks
            from scoring_engine import run_scoring
        except ImportError:
            from api.data_fetcher import batch_update_stocks_parallel, batch_update_stocks
            from api.scoring_engine import run_scoring
        tickers = get_all_tickers(use_full=True, limit=universe_size) if universe_size > 0 else get_all_tickers()
        data = batch_update_stocks_parallel(tickers, force_refresh=True, max_workers=10) if len(tickers) > 200 else batch_update_stocks(tickers, force_refresh=True)
        if data:
            db.save_scan_cache(data)
            df, lh, c, ra = run_scoring(data)
            if not df.empty:
                g1 = df[df.get("GURJAS_1", False) == True].to_dict("records") if "GURJAS_1" in df.columns else []
                g2 = df[df.get("GURJAS_2", False) == True].to_dict("records") if "GURJAS_2" in df.columns else []
                db.save_gurjas_results("GURJAS1", g1)
                db.save_gurjas_results("GURJAS 1", g1)
                db.save_gurjas_results("GURJAS2", g2)
                db.save_gurjas_results("GURJAS 2", g2)
                meta = {"last_scan_time": datetime.datetime.now().isoformat(), "total_stocks": len(data), "scan_mode": "Full Universe"}
                db.save_scan_meta(meta)
    except Exception as e:
        print(f"Background scan error: {e}")
    finally:
        _scan_running = False

@app.post("/scan/run")
@app.post("/api/scan/run")
def trigger_scan(universe: int = Query(default=0), background_tasks: BackgroundTasks = None):
    if background_tasks:
        background_tasks.add_task(_run_scan_job, universe)
    return {
        "status": "scan_started",
        "message": f"Scan triggered for universe {universe}.",
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/scan/status")
@app.get("/api/scan/status")
def get_scan_status():
    try:
        meta = db.get_scan_meta() or {}
    except Exception as e:
        print(f"Error getting scan meta: {e}")
        meta = {}
    return {
        "scan_running": _scan_running,
        "last_scan_time": meta.get("last_scan_time"),
        "total_stocks": meta.get("total_stocks", 0),
        "scan_mode": meta.get("scan_mode", "Full Universe"),
    }

@app.get("/stocks")
@app.get("/api/stocks")
def get_stock_symbols():
    """Returns all stock ticker symbols for auto-complete."""
    try:
        tickers = get_all_tickers(use_full=True)
        symbols = sorted([t.replace(".NS", "") for t in tickers])
        return {"count": len(symbols), "symbols": symbols}
    except Exception as e:
        print(f"Error fetching stock symbols: {e}")
        # Fallback to core stocks
        tickers = get_all_tickers(use_full=False)
        symbols = sorted([t.replace(".NS", "") for t in tickers])
        return {"count": len(symbols), "symbols": symbols}

@app.get("/scan/results/gurjas1")
@app.get("/api/scan/results/gurjas1")
def get_gurjas1_results():
    try:
        results = db.load_gurjas_results("GURJAS1")
        if not results:
            results = db.load_gurjas_results("GURJAS 1")
    except Exception as e:
        print(f"Error loading GURJAS 1: {e}")
        results = []
    return {
        "screener": "GURJAS 1",
        "count": len(results),
        "stocks": results,
    }

@app.get("/scan/results/gurjas2")
@app.get("/api/scan/results/gurjas2")
def get_gurjas2_results():
    try:
        results = db.load_gurjas_results("GURJAS2")
        if not results:
            results = db.load_gurjas_results("GURJAS 2")
    except Exception as e:
        print(f"Error loading GURJAS 2: {e}")
        results = []
    return {
        "screener": "GURJAS 2",
        "count": len(results),
        "stocks": results,
    }

@app.get("/api/users")
def list_users():
    users = db.get_all_users()
    return {"users": users}

@app.post("/api/users")
def create_new_user(user: UserCreate):
    uid = db.create_user(user.name, user.email)
    return {"status": "created", "user_id": uid, "name": user.name}

@app.get("/portfolio/{user_id}")
@app.get("/api/portfolio/{user_id}")
def get_portfolio(user_id: int):
    try:
        holdings = db.load_portfolio_db(user_id)
        return {"user_id": user_id, "count": len(holdings), "holdings": holdings}
    except Exception as e:
        print(f"Error loading portfolio user {user_id}: {e}\n{traceback.format_exc()}")
        return {"user_id": user_id, "count": 0, "holdings": [], "error": str(e)}

def _add_holding_logic(user_id: int, h: HoldingAdd):
    try:
        target_user = user_id if user_id else (h.user_id if h.user_id else 1)
        holdings = db.load_portfolio_db(target_user)
        sym = h.symbol.strip().upper()

        ltp, sma = None, None
        try:
            cache = db.load_scan_cache()
            for key in [sym, f"{sym}.NS"]:
                if key in cache and cache[key].get("ltp"):
                    ltp = float(cache[key].get("ltp"))
                    sma = float(cache[key].get("sma_200", cache[key].get("dma_200", 0.0)))
                    break
        except Exception:
            pass

        if ltp is None:
            try:
                from portfolio_manager import fetch_ltp_and_sma
                ltp, sma = fetch_ltp_and_sma(sym)
            except Exception:
                pass

        final_ltp = float(ltp) if ltp else float(h.buy_price)
        final_sma = float(sma) if sma else 0.0
        above = final_ltp >= final_sma if final_sma > 0 else True
        dist = round(((final_ltp - final_sma) / final_sma) * 100.0, 2) if final_sma > 0 else 0.0

        signal = "WAIT"
        if final_sma > 0:
            if not above:
                signal = "EXIT"
            elif dist < 15:
                signal = "BUY"
            else:
                signal = "HOLD"

        new_h = {
            "symbol": sym,
            "buy_price": float(h.buy_price),
            "quantity": float(h.quantity),
            "buy_date": h.buy_date or datetime.date.today().isoformat(),
            "ltp": final_ltp,
            "sma_200": final_sma,
            "above_sma": above,
            "dist_pct": dist,
            "signal": signal,
            "signal_strength": 3 if signal != "WAIT" else 0,
        }
        updated = [x for x in holdings if x.get("symbol") != new_h["symbol"]]
        updated.append(new_h)
        db.save_portfolio_db(target_user, updated)
        return {"status": "added", "symbol": new_h["symbol"], "count": len(updated), "holdings": updated}
    except Exception as e:
        err_msg = f"Failed to add holding: {str(e)}"
        print(f"Error adding holding: {err_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=err_msg)

@app.post("/portfolio/add")
@app.post("/api/portfolio/add")
def add_portfolio_holding_body(h: HoldingAdd):
    return _add_holding_logic(h.user_id, h)

@app.post("/portfolio/{user_id}/add")
@app.post("/api/portfolio/{user_id}/add")
def add_portfolio_holding_path(user_id: int, h: HoldingAdd):
    return _add_holding_logic(user_id, h)

@app.delete("/portfolio/{user_id}/{symbol}")
@app.delete("/api/portfolio/{user_id}/{symbol}")
def delete_portfolio_holding(user_id: int, symbol: str):
    try:
        holdings = db.load_portfolio_db(user_id)
        updated = [x for x in holdings if x.get("symbol") != symbol.upper()]
        db.save_portfolio_db(user_id, updated)
        return {"status": "deleted", "symbol": symbol.upper(), "remaining": len(updated), "holdings": updated}
    except Exception as e:
        err_msg = f"Failed to remove holding: {str(e)}"
        print(f"Error deleting holding: {err_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=err_msg)

@app.post("/portfolio/sync")
@app.post("/api/portfolio/sync")
def sync_portfolio_prices():
    try:
        try:
            from portfolio_manager import update_portfolio_prices
        except ImportError:
            from api.portfolio_manager import update_portfolio_prices
        users = db.get_all_users()
        synced_users = []
        for u in users:
            uid = u["id"]
            holdings = db.load_portfolio_db(uid)
            if holdings:
                updated = update_portfolio_prices(holdings, user_id=uid)
                db.save_portfolio_db(uid, updated)
                synced_users.append(u["name"])
        return {"status": "synced", "users_synced": synced_users}
    except Exception as e:
        err_msg = f"Sync failed: {str(e)}"
        print(f"Error syncing portfolio: {err_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=err_msg)

@app.get("/api/scan/cache/{ticker}")
def get_stock_cache(ticker: str):
    cache = db.load_scan_cache()
    stock_info = cache.get(ticker.upper(), {})
    return {"symbol": ticker.upper(), "data": stock_info}

@app.get("/api/analysis/{symbol}")
@app.post("/api/ai/ask")
def ask_jarvis_ai(symbol: Optional[str] = None, req: Optional[StockAsk] = None):
    sym = (symbol or (req.symbol if req else "")).upper()
    cache = db.load_scan_cache()
    stock_info = cache.get(sym, {})
    if not stock_info:
        stock_info = {"symbol": sym, "ltp": 0.0}
    
    analysis = generate_ai_narrative(sym, stock_info)
    return {
        "symbol": sym,
        "ai_active": has_active_api_key(),
        "analysis": analysis,
    }

# Vercel handler export
handler = app
