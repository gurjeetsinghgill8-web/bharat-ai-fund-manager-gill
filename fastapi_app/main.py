"""
fastapi_app/main.py — Bharat AI Fund Manager Gill — FastAPI Backend
Phase 2 / Brick 2.1

Replaces Streamlit as the backend engine.
Deployed to Hugging Face Spaces (Docker SDK).

All Python logic (scoring, scraping, portfolio, LLM) is imported directly.
Supabase is the permanent database — nothing is lost on restart.

Architecture:
  React Frontend (Vercel) → HTTPS → THIS FastAPI app (HF Spaces) → Supabase (PostgreSQL)

Startup behaviour:
  On every cold start, checks if today's scan has been done.
  If not, runs a catch-up scan in the background automatically.
  This handles HF Spaces sleep gracefully.
"""

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

# ── Load env from parent directory (HF Spaces: /app, local: project root) ────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
load_dotenv(os.path.join(_ROOT, ".env"))
sys.path.insert(0, _ROOT)   # so we can import all project modules

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Project imports ────────────────────────────────────────────────────────────
import supabase_db as db
from symbols import get_all_tickers
from data_fetcher import batch_update_stocks_parallel, batch_update_stocks
from scoring_engine import run_scoring
from portfolio_manager import update_portfolio_prices, check_and_trigger_alerts
from llm_harness import generate_ai_narrative, has_active_api_key

# ── Config ─────────────────────────────────────────────────────────────────────
API_SECRET = os.getenv("FASTAPI_SECRET_KEY", "bharat-ai-secret-2026")  # Set in HF Spaces secrets
ALLOWED_ORIGINS = [
    "http://localhost:5173",         # Vite dev server
    "http://localhost:3000",
    "https://*.vercel.app",          # All Vercel preview deployments
    os.getenv("FRONTEND_URL", ""),   # Production Vercel URL
]

# ── Background scan state ───────────────────────────────────────────────────────
_scan_running = False


# ══════════════════════════════════════════════════════════════════════════════
# LIFESPAN — Startup Catch-Up Scan
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup. Checks if today's scan is done.
    If HF Space was sleeping and missed today's scan, triggers a background catch-up.
    """
    print("=" * 60)
    print("  BHARAT AI FUND MANAGER — FastAPI Backend Starting")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("=" * 60)

    # Verify Supabase connection
    try:
        db.init_db()
    except Exception as e:
        print(f"[WARN] Supabase warning on startup: {e}")

    # Catch-up scan check
    try:
        meta = db.get_scan_meta()
        last_scan = meta.get("last_scan_time")
        today = datetime.date.today()

        needs_scan = True
        if last_scan:
            if isinstance(last_scan, str):
                last_scan_date = datetime.datetime.fromisoformat(last_scan.replace("Z", "+00:00")).date()
            else:
                last_scan_date = last_scan.date()
            needs_scan = last_scan_date < today

        if needs_scan:
            print(f"[CATCH-UP] No scan found for today ({today}) — triggering background catch-up scan...")
            asyncio.create_task(_background_scan(universe_size=0))
        else:
            print(f"[OK] Today's scan already done (last: {last_scan}) — skipping catch-up")
    except Exception as e:
        print(f"[WARN] Catch-up scan check failed: {e}")

    yield  # App runs here

    print("[INFO] Bharat AI FastAPI shutting down")


# ══════════════════════════════════════════════════════════════════════════════
# APP INIT
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Bharat AI Fund Manager Gill — API",
    description="FastAPI backend for GURJAS screener, portfolio management, and AI analysis.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten to ALLOWED_ORIGINS after frontend URL is known
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ══════════════════════════════════════════════════════════════════════════════

async def _background_scan(universe_size: int = 0):
    """
    Runs full stock scan in background.
    Saves GURJAS 1 & 2 results to Supabase when done.
    """
    global _scan_running
    if _scan_running:
        print("⚠️  Scan already running — skipping duplicate trigger")
        return

    _scan_running = True
    try:
        print(f"[SCAN] Starting background scan at {datetime.datetime.now()}")

        tickers = get_all_tickers(use_full=True, limit=universe_size) if universe_size > 0 else get_all_tickers()
        print(f"[SCAN] Universe: {len(tickers)} stocks")

        # Fetch data
        if len(tickers) > 200:
            data = batch_update_stocks_parallel(tickers, force_refresh=True, max_workers=10)
        else:
            data = batch_update_stocks(tickers, force_refresh=True)

        if not data:
            print("[SCAN] No data returned — aborting")
            return

        # Save raw cache
        db.save_scan_cache(data)

        # Run scoring
        df, latest_highs, continuous, red_alerts = run_scoring(data)

        if df.empty:
            print("[SCAN] Scored df is empty")
            return

        # Save GURJAS results
        gurjas1_rows = df[df.get("GURJAS_1", False) == True].to_dict("records") if "GURJAS_1" in df.columns else []
        gurjas2_rows = df[df.get("GURJAS_2", False) == True].to_dict("records") if "GURJAS_2" in df.columns else []

        db.save_gurjas_results("GURJAS1", gurjas1_rows)
        db.save_gurjas_results("GURJAS2", gurjas2_rows)

        print(f"[SCAN] Done — GURJAS1: {len(gurjas1_rows)}, GURJAS2: {len(gurjas2_rows)} stocks saved")

    except Exception as e:
        print(f"[SCAN] Error: {e}")
        traceback.print_exc()
    finally:
        _scan_running = False


async def _background_portfolio_sync():
    """Syncs portfolio prices for ALL users and triggers 200 SMA alerts."""
    try:
        print(f"[SYNC] Portfolio sync starting at {datetime.datetime.now()}")
        user_ids = db.get_all_user_ids_with_portfolios()
        all_users = {u["id"]: (u["name"], u.get("email")) for u in db.get_all_users()}

        for uid in user_ids:
            user_name, user_email = all_users.get(uid, (f"User #{uid}", None))
            portfolio = db.load_portfolio_db(uid)
            if not portfolio:
                continue
            portfolio = update_portfolio_prices(portfolio, user_id=uid)
            db.save_portfolio_db(uid, portfolio)
            print(f"[SYNC] Synced {len(portfolio)} holdings for '{user_name}'")

        print("[SYNC] Portfolio sync complete")
    except Exception as e:
        print(f"[SYNC] Error: {e}")
        traceback.print_exc()


# ══════════════════════════════════════════════════════════════════════════════
# AUTH HELPER
# ══════════════════════════════════════════════════════════════════════════════

def _check_auth(x_api_key: Optional[str]):
    """Simple API key auth for protected endpoints."""
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════════════════════

class CreateUserRequest(BaseModel):
    name: str
    email: Optional[str] = None

class AddHoldingRequest(BaseModel):
    symbol: str
    buy_price: float
    quantity: int

class UpdateEmailRequest(BaseModel):
    email: str


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — HEALTH & WAKE
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Bharat AI Fund Manager Gill — API",
        "version": "2.0.0",
        "status": "running",
        "time": datetime.datetime.now().isoformat(),
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check + Supabase ping. Used by Vercel cron to keep HF Space warm."""
    try:
        meta = db.get_scan_meta()
        return {
            "status": "healthy",
            "scan_running": _scan_running,
            "last_scan": meta.get("last_scan_time"),
            "total_stocks": meta.get("total_stocks", 0),
            "time": datetime.datetime.now().isoformat(),
        }
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": str(e)})


@app.get("/api/wake", tags=["Health"])
async def wake():
    """Vercel cron endpoint — pings to prevent HF Space from sleeping."""
    return {"status": "awake", "time": datetime.datetime.now().isoformat()}


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — SCAN
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/scan/run", tags=["Scan"])
async def trigger_scan(
    background_tasks: BackgroundTasks,
    universe: int = Query(default=0, description="0=Core 127, 500, 1000, 2000, 4000"),
    x_api_key: Optional[str] = Header(default=None),
):
    """Trigger a full stock scan (runs in background). Protected endpoint."""
    _check_auth(x_api_key)
    if _scan_running:
        return {"status": "already_running", "message": "Scan is already in progress"}

    background_tasks.add_task(_background_scan, universe_size=universe)
    return {
        "status": "started",
        "universe": universe or "Core 127",
        "message": "Scan started in background. Check /api/scan/status for progress.",
    }


@app.get("/api/scan/status", tags=["Scan"])
async def scan_status():
    """Returns scan running state and last scan metadata."""
    meta = db.get_scan_meta()
    return {
        "scan_running": _scan_running,
        "last_scan_time": meta.get("last_scan_time"),
        "total_stocks":   meta.get("total_stocks", 0),
        "scan_mode":      meta.get("scan_mode", "Core 127"),
    }


@app.get("/api/scan/results/gurjas1", tags=["Scan"])
async def get_gurjas1_results():
    """Returns latest GURJAS 1 screener results."""
    try:
        results = db.load_gurjas_results("GURJAS1")
        if not results:
            results = db.load_gurjas_results("GURJAS 1")
    except Exception as e:
        print(f"Error loading GURJAS 1: {e}")
        results = []
    return {"screener": "GURJAS1", "count": len(results), "stocks": results}


@app.get("/api/scan/results/gurjas2", tags=["Scan"])
async def get_gurjas2_results():
    """Returns latest GURJAS 2 screener results."""
    try:
        results = db.load_gurjas_results("GURJAS2")
        if not results:
            results = db.load_gurjas_results("GURJAS 2")
    except Exception as e:
        print(f"Error loading GURJAS 2: {e}")
        results = []
    return {"screener": "GURJAS2", "count": len(results), "stocks": results}


@app.get("/api/scan/cache/{ticker}", tags=["Scan"])
async def get_stock_data(ticker: str):
    """Returns cached financial data for a single stock ticker."""
    cache = db.load_scan_cache()
    ticker_upper = ticker.upper()
    if ticker_upper not in cache:
        ticker_ns = ticker_upper + ".NS"
        if ticker_ns not in cache:
            raise HTTPException(status_code=404, detail=f"No data for ticker: {ticker}")
        return {"ticker": ticker_ns, "data": cache[ticker_ns]}
    return {"ticker": ticker_upper, "data": cache[ticker_upper]}


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — USERS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/users", tags=["Users"])
async def list_users():
    """Returns all user profiles."""
    users = db.get_all_users()
    return {"users": users, "count": len(users)}


@app.post("/api/users", tags=["Users"])
async def create_user(req: CreateUserRequest):
    """Creates a new user (or returns existing). Returns user_id."""
    user_id = db.create_user(name=req.name, email=req.email)
    user = db.get_user_by_name(req.name)
    return {"user_id": user_id, "user": user}


@app.put("/api/users/{user_id}/email", tags=["Users"])
async def update_email(user_id: int, req: UpdateEmailRequest):
    """Updates a user's email address."""
    db.update_user_email(user_id, req.email)
    return {"success": True, "user_id": user_id, "email": req.email}


@app.delete("/api/users/{user_id}", tags=["Users"])
async def delete_user(user_id: int, x_api_key: Optional[str] = Header(default=None)):
    """Deletes a user and all their holdings. Protected."""
    _check_auth(x_api_key)
    db.delete_user(user_id)
    return {"success": True, "deleted_user_id": user_id}


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/portfolio/{user_id}", tags=["Portfolio"])
async def get_portfolio(user_id: int):
    """Returns all holdings for a user."""
    holdings = db.load_portfolio_db(user_id)
    return {"user_id": user_id, "count": len(holdings), "holdings": holdings}


@app.post("/api/portfolio/{user_id}/add", tags=["Portfolio"])
async def add_holding(user_id: int, req: AddHoldingRequest):
    """Adds or updates a holding for a user."""
    # Normalize symbol — add .NS if not present
    symbol = req.symbol.upper()
    if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
        symbol += ".NS"

    updated = db.add_holding_db(user_id, symbol, req.buy_price, req.quantity)
    return {"success": True, "user_id": user_id, "symbol": symbol, "holdings": updated}


@app.delete("/api/portfolio/{user_id}/{symbol}", tags=["Portfolio"])
async def remove_holding(user_id: int, symbol: str):
    """Removes a holding from a user's portfolio."""
    symbol_upper = symbol.upper()
    if not symbol_upper.endswith(".NS") and not symbol_upper.endswith(".BO"):
        symbol_upper += ".NS"
    updated = db.remove_holding_db(user_id, symbol_upper)
    return {"success": True, "user_id": user_id, "symbol": symbol_upper, "holdings": updated}


@app.post("/api/portfolio/sync", tags=["Portfolio"])
async def sync_portfolios(background_tasks: BackgroundTasks):
    """
    Triggers portfolio price sync for ALL users (background).
    Sends 200 SMA breach alerts via email.
    """
    background_tasks.add_task(_background_portfolio_sync)
    return {"status": "started", "message": "Portfolio sync running in background"}


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — AI ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/analysis/{symbol}", tags=["AI Analysis"])
async def ai_analysis(symbol: str):
    """
    Returns JARVIS AI analysis for a stock symbol.
    Uses llm_harness.py with Groq → xAI → Gemini auto-failover.
    """
    try:
        symbol_upper = symbol.upper()
        if not symbol_upper.endswith(".NS") and not symbol_upper.endswith(".BO"):
            symbol_upper += ".NS"

        # Get cached stock data
        cache = db.load_scan_cache()
        stock_data = cache.get(symbol_upper) or cache.get(symbol.upper())

        if not stock_data:
            raise HTTPException(status_code=404, detail=f"No cached data for {symbol}. Run a scan first.")

        if not has_active_api_key():
            raise HTTPException(status_code=503, detail="No AI API key configured")

        # Run LLM analysis
        analysis = generate_ai_narrative(stock_data, symbol=symbol_upper)
        return {
            "symbol": symbol_upper,
            "analysis": analysis,
            "generated_at": datetime.datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES — VERCEL CRON ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/cron/daily-scan", tags=["Cron"])
async def cron_daily_scan(
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(default=None),
):
    """Called by Vercel cron at 10 AM IST daily. Triggers full scan + portfolio sync."""
    _check_auth(x_api_key)
    if not _scan_running:
        background_tasks.add_task(_background_scan, universe_size=0)
    background_tasks.add_task(_background_portfolio_sync)
    return {"status": "triggered", "time": datetime.datetime.now().isoformat()}


@app.get("/api/cron/wake", tags=["Cron"])
async def cron_wake():
    """Called by Vercel cron to keep HF Space warm. No auth required."""
    return {"status": "awake", "time": datetime.datetime.now().isoformat()}
