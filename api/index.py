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
    from data_fetcher import batch_update_stocks_parallel, batch_update_stocks
    from scoring_engine import run_scoring
    from portfolio_manager import update_portfolio_prices, check_and_trigger_alerts
    from llm_harness import generate_ai_narrative, has_active_api_key
except ImportError:
    from api import supabase_db as db
    from api.symbols import get_all_tickers
    from api.data_fetcher import batch_update_stocks_parallel, batch_update_stocks
    from api.scoring_engine import run_scoring
    from api.portfolio_manager import update_portfolio_prices, check_and_trigger_alerts
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

@app.post("/scan/run")
@app.post("/api/scan/run")
def trigger_scan(universe: int = Query(default=0)):
    global _scan_running
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

@app.get("/api/portfolio/{user_id}")
def get_portfolio(user_id: int):
    holdings = db.load_portfolio_db(user_id)
    return {"user_id": user_id, "count": len(holdings), "holdings": holdings}

@app.post("/api/portfolio/add")
def add_portfolio_holding(h: HoldingAdd):
    holdings = db.load_portfolio_db(h.user_id)
    new_h = {
        "symbol": h.symbol.upper(),
        "buy_price": h.buy_price,
        "quantity": h.quantity,
        "buy_date": h.buy_date or datetime.date.today().isoformat(),
        "ltp": h.buy_price,
    }
    updated = [x for x in holdings if x.get("symbol") != new_h["symbol"]]
    updated.append(new_h)
    db.save_portfolio_db(h.user_id, updated)
    return {"status": "added", "symbol": new_h["symbol"], "total_holdings": len(updated)}

@app.delete("/api/portfolio/{user_id}/{symbol}")
def delete_portfolio_holding(user_id: int, symbol: str):
    holdings = db.load_portfolio_db(user_id)
    updated = [x for x in holdings if x.get("symbol") != symbol.upper()]
    db.save_portfolio_db(user_id, updated)
    return {"status": "deleted", "symbol": symbol.upper(), "remaining": len(updated)}

@app.post("/api/portfolio/sync")
def sync_portfolio_prices():
    users = db.get_all_users()
    synced_users = []
    for u in users:
        uid = u["id"]
        holdings = db.load_portfolio_db(uid)
        if holdings:
            updated = update_portfolio_prices(holdings)
            db.save_portfolio_db(uid, updated)
            synced_users.append(u["name"])
    return {"status": "synced", "users_synced": synced_users}

@app.post("/api/ai/ask")
def ask_jarvis_ai(req: StockAsk):
    cache = db.load_scan_cache()
    stock_info = cache.get(req.symbol.upper(), {})
    if not stock_info:
        stock_info = {"symbol": req.symbol.upper(), "ltp": 0.0}
    
    analysis = generate_ai_narrative(req.symbol.upper(), stock_info)
    return {
        "symbol": req.symbol.upper(),
        "ai_active": has_active_api_key(),
        "analysis": analysis,
    }

# Vercel handler export
handler = app
