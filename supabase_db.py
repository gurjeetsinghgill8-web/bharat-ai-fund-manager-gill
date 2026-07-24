"""
supabase_db.py — Supabase (PostgreSQL) Persistent Storage Engine
               for Bharat AI Fund Manager Gill

Phase 1 / Brick 1.3 — v2 (Direct REST via httpx — no supabase-py package)

Drop-in replacement for db.py — EXACT same function signatures.

Uses Supabase PostgREST API directly via httpx.
This avoids the supabase-py / websockets / realtime dependency conflict.

Setup:
    pip install httpx
    Set in .env:
        SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
        SUPABASE_SERVICE_KEY=eyJhbGci...  (service_role key — NOT anon key)
"""

import os
import json
import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# LAZY httpx import — only fails at call time, not on import
# ---------------------------------------------------------------------------
try:
    import httpx
    _HTTPX_OK = True
except ImportError:
    _HTTPX_OK = False

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

_CONFIGURED = (
    SUPABASE_URL
    and SUPABASE_SERVICE_KEY
    and "YOUR_PROJECT_ID" not in SUPABASE_URL
    and "YOUR_SERVICE_ROLE_KEY" not in SUPABASE_SERVICE_KEY
)

REST_BASE = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ""


def _headers(prefer: str = "") -> dict:
    """Returns Supabase PostgREST auth headers."""
    h = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def _client() -> "httpx.Client":
    """Returns a configured httpx client with 30s timeout."""
    return httpx.Client(timeout=httpx.Timeout(30.0, connect=15.0))


def _execute_with_retry(func, retries=3):
    """Executes a request function with up to N retries on timeout/network errors."""
    for attempt in range(retries):
        try:
            return func()
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt == retries - 1:
                raise
            import time
            time.sleep(0.5 * (attempt + 1))


def _get(table: str, params: dict = None) -> list[dict]:
    """SELECT from a table."""
    _require_config()
    def op():
        with _client() as c:
            r = c.get(f"{REST_BASE}/{table}", headers=_headers(), params=params or {})
            r.raise_for_status()
            return r.json()
    return _execute_with_retry(op)


def _post(table: str, data, prefer: str = "return=representation") -> list[dict]:
    """INSERT into a table."""
    _require_config()
    def op():
        with _client() as c:
            r = c.post(
                f"{REST_BASE}/{table}",
                headers=_headers(prefer),
                content=json.dumps(data),
            )
            if r.status_code >= 400:
                print(f"[Supabase REST Error {r.status_code}] Table: {table} | Body: {r.text}")
            r.raise_for_status()
            return r.json() if r.text else []
    return _execute_with_retry(op)


def _patch(table: str, filters: dict, data: dict) -> list[dict]:
    """UPDATE rows matching filters."""
    _require_config()
    params = {k: f"eq.{v}" for k, v in filters.items()}
    def op():
        with _client() as c:
            r = c.patch(
                f"{REST_BASE}/{table}",
                headers=_headers("return=representation"),
                params=params,
                content=json.dumps(data),
            )
            r.raise_for_status()
            return r.json() if r.text else []
    return _execute_with_retry(op)


def _delete(table: str, filters: dict):
    """DELETE rows matching filters."""
    _require_config()
    params = {k: f"eq.{v}" for k, v in filters.items()}
    def op():
        with _client() as c:
            r = c.delete(f"{REST_BASE}/{table}", headers=_headers(), params=params)
            r.raise_for_status()
    return _execute_with_retry(op)


def _upsert(table: str, data, on_conflict: str = "") -> list[dict]:
    """UPSERT (insert or update on conflict)."""
    _require_config()
    prefer = "resolution=merge-duplicates,return=representation"
    params = {}
    if on_conflict:
        params["on_conflict"] = on_conflict
    def op():
        with _client() as c:
            r = c.post(
                f"{REST_BASE}/{table}",
                headers=_headers(prefer),
                params=params,
                content=json.dumps(data),
            )
            if r.status_code >= 400:
                print(f"[Supabase REST Error {r.status_code}] Table: {table} | Body: {r.text}")
            r.raise_for_status()
            return r.json() if r.text else []
    return _execute_with_retry(op)


def _require_config():
    if not _CONFIGURED:
        raise RuntimeError(
            "Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env"
        )
    if not _HTTPX_OK:
        raise RuntimeError("httpx not installed. Run: pip install httpx")


# ---------------------------------------------------------------------------
# INIT
# ---------------------------------------------------------------------------

def init_db():
    """
    Compatibility shim — tables created via supabase_schema.sql.
    Verifies connection if configured, silently skips if not.
    """
    if not _CONFIGURED:
        print("[Supabase] Not configured yet — skipping init (fill in .env first)")
        return
    try:
        _get("scan_meta", {"select": "id", "limit": "1"})
        print("[Supabase] Connection OK")
    except Exception as e:
        print(f"[Supabase] Connection warning: {e}")


# ---------------------------------------------------------------------------
# USER MANAGEMENT
# ---------------------------------------------------------------------------

def create_user(name: str, email: str = None) -> int:
    existing = _get("users", {"select": "id,email", "name": f"eq.{name}", "limit": "1"})
    if existing:
        uid = existing[0]["id"]
        if email is not None:
            _patch("users", {"id": uid}, {"email": email})
        return uid
    rows = _post("users", {"name": name, "email": email})
    return rows[0]["id"]


def update_user_email(user_id: int, email: str):
    _patch("users", {"id": user_id}, {"email": email})


def get_all_users() -> list[dict]:
    return _get("users", {"select": "id,name,email,created_at", "order": "id"})


def get_user_by_name(name: str) -> Optional[dict]:
    rows = _get("users", {"select": "id,name,email,created_at", "name": f"eq.{name}", "limit": "1"})
    return rows[0] if rows else None


def delete_user(user_id: int):
    _delete("users", {"id": user_id})


def ensure_user(user_id: int = 1) -> int:
    """Ensures user exists in users table to satisfy foreign key constraints."""
    try:
        users = get_all_users()
        if not users or not any(u["id"] == user_id for u in users):
            return create_user("Gurjas")
    except Exception as e:
        print(f"[Supabase] ensure_user warning: {e}")
    return user_id


# ---------------------------------------------------------------------------
# PORTFOLIO CRUD
# ---------------------------------------------------------------------------

def load_portfolio_db(user_id: int) -> list[dict]:
    rows = _get("portfolios", {
        "select": "*",
        "user_id": f"eq.{user_id}",
        "order": "symbol",
    })
    holdings = []
    for r in rows:
        holdings.append({
            "symbol":              r["symbol"],
            "buy_price":           r["buy_price"],
            "quantity":            r["quantity"],
            "ltp":                 r["ltp"],
            "sma_200":             r["sma_200"],
            "dist_pct":            r["dist_pct"],
            "above_sma":           bool(r["above_sma"]),
            "signal":              r["signal"],
            "signal_strength":     r["signal_strength"],
            "last_updated":        r["last_updated"],
            "_alert_emailed_date": r.get("alert_emailed_date") or "",
        })
    return holdings


def save_portfolio_db(user_id: int, holdings: list[dict]):
    ensure_user(user_id)
    _delete("portfolios", {"user_id": user_id})
    if not holdings:
        return

    seen_symbols = set()
    rows = []
    for h in holdings:
        sym = str(h["symbol"]).upper()
        if sym in seen_symbols:
            continue
        seen_symbols.add(sym)
        alert_date = h.get("_alert_emailed_date", "") or None
        if alert_date == "":
            alert_date = None
        rows.append({
            "user_id":            int(user_id),
            "symbol":             sym,
            "buy_price":          float(h.get("buy_price", 0.0)),
            "quantity":           int(h.get("quantity", 0)),
            "ltp":                float(h.get("ltp", 0.0)),
            "sma_200":            float(h.get("sma_200", 0.0)),
            "dist_pct":           float(h.get("dist_pct", 0.0)),
            "above_sma":          bool(h.get("above_sma", False)),
            "signal":             str(h.get("signal", "WAIT")),
            "signal_strength":    int(h.get("signal_strength", 0)),
            "last_updated":       h.get("last_updated"),
            "alert_emailed_date": alert_date,
        })

    # Batch insert (max 500 per request)
    for i in range(0, len(rows), 500):
        _post("portfolios", rows[i:i + 500])


def add_holding_db(user_id: int, symbol: str, buy_price: float, quantity: int) -> list[dict]:
    _upsert("portfolios", {
        "user_id":   user_id,
        "symbol":    symbol,
        "buy_price": buy_price,
        "quantity":  quantity,
    }, on_conflict="user_id,symbol")
    return load_portfolio_db(user_id)


def remove_holding_db(user_id: int, symbol: str) -> list[dict]:
    _require_config()
    with _client() as c:
        r = c.delete(
            f"{REST_BASE}/portfolios",
            headers=_headers(),
            params={"user_id": f"eq.{user_id}", "symbol": f"eq.{symbol}"},
        )
        r.raise_for_status()
    return load_portfolio_db(user_id)


def get_all_user_ids_with_portfolios() -> list[int]:
    rows = _get("portfolios", {"select": "user_id"})
    return list(set(r["user_id"] for r in rows))


# ---------------------------------------------------------------------------
# SCAN CACHE
# ---------------------------------------------------------------------------

def save_scan_cache(stock_data_dict: dict):
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = [
        {"ticker": ticker, "data": _make_serializable(data), "updated_at": now_str}
        for ticker, data in stock_data_dict.items()
    ]

    # Batch upsert 500 at a time
    for i in range(0, len(rows), 500):
        _upsert("scan_cache", rows[i:i + 500], on_conflict="ticker")

    # Update scan_meta
    _upsert("scan_meta", {
        "id":             1,
        "last_scan_time": now_str,
        "total_stocks":   len(stock_data_dict),
    }, on_conflict="id")

    print(f"[Supabase] Scan cache saved ({len(stock_data_dict)} stocks)")


def load_scan_cache() -> dict:
    result = {}
    offset = 0
    limit = 1000
    while True:
        rows = _get("scan_cache", {
            "select": "ticker,data",
            "limit": str(limit),
            "offset": str(offset),
        })
        if not rows:
            break
        for r in rows:
            result[r["ticker"]] = r["data"]
        if len(rows) < limit:
            break
        offset += limit
    return result


def get_scan_meta() -> dict:
    rows = _get("scan_meta", {"select": "*", "id": "eq.1", "limit": "1"})
    if rows:
        return rows[0]
    return {"last_scan_time": None, "total_stocks": 0, "scan_mode": "Core 127"}


def save_scan_meta(meta: dict):
    _require_config()
    payload = {
        "id": 1,
        "last_scan_time": meta.get("last_scan_time") or datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_stocks": meta.get("total_stocks", 0),
        "scan_mode": meta.get("scan_mode", "Full Universe"),
    }
    with _client() as c:
        r = c.post(
            f"{REST_BASE}/scan_meta",
            headers=_headers("resolution=merge-duplicates"),
            content=json.dumps(payload),
        )
        r.raise_for_status()


def clear_scan_cache():
    _require_config()
    # Delete all rows — filter neq on ticker (always true)
    with _client() as c:
        r = c.delete(
            f"{REST_BASE}/scan_cache",
            headers=_headers(),
            params={"ticker": "neq.XXXXXX_NEVER_EXISTS"},
        )
        r.raise_for_status()


# ---------------------------------------------------------------------------
# GURJAS RESULTS
# ---------------------------------------------------------------------------

def save_gurjas_results(screener: str, results: list[dict]):
    clean_screener = screener.replace(" ", "").upper()
    _delete("gurjas_results", {"screener": clean_screener})
    if not results:
        return

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = [
        {
            "screener":   clean_screener,
            "symbol":     r.get("symbol") or r.get("ticker", ""),
            "data":       _make_serializable(r),
            "scanned_at": now_str,
        }
        for r in results
    ]
    for i in range(0, len(rows), 500):
        _post("gurjas_results", rows[i:i + 500])

    print(f"[Supabase] Saved {len(results)} {clean_screener} results")


def load_gurjas_results(screener: str) -> list[dict]:
    clean_screener = screener.replace(" ", "").upper()
    rows = _get("gurjas_results", {
        "select": "symbol,data,scanned_at",
        "screener": f"eq.{clean_screener}",
        "order": "scanned_at.desc",
        "limit": "1000",
    })
    return [r["data"] for r in rows]


# ---------------------------------------------------------------------------
# MIGRATION
# ---------------------------------------------------------------------------

def migrate_from_json(json_path: str = "portfolio_store.json", default_user_name: str = "Gurjas") -> bool:
    if not os.path.exists(json_path):
        return False
    try:
        with open(json_path, "r") as f:
            old_data = json.load(f)

        if isinstance(old_data, dict) and "users" in old_data:
            for user_name, holdings in old_data["users"].items():
                if not holdings:
                    continue
                user_id = create_user(user_name)
                if not load_portfolio_db(user_id):
                    save_portfolio_db(user_id, holdings)
                    print(f"[Supabase] Migrated {len(holdings)} holdings for '{user_name}'")
            return True

        elif isinstance(old_data, list) and old_data:
            user_id = create_user(default_user_name)
            if not load_portfolio_db(user_id):
                save_portfolio_db(user_id, old_data)
                print(f"[Supabase] Migrated {len(old_data)} holdings (user: {default_user_name})")
                return True

        return False
    except Exception as e:
        print(f"Migration error: {e}")
        return False


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

import math

def _clean_val(v):
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _clean_val(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_clean_val(item) for item in v]
    if isinstance(v, (str, int, bool, type(None))):
        return v
    return str(v)

def _make_serializable(data: dict) -> dict:
    if not isinstance(data, dict):
        return {}
    return {k: _clean_val(v) for k, v in data.items()}


# ---------------------------------------------------------------------------
# INIT: Run on import
# ---------------------------------------------------------------------------
init_db()
