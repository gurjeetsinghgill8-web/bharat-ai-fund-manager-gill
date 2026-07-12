"""
db.py — SQLite Persistent Storage Engine for Bharat AI Fund Manager Gill

This is the PERMANENT MEMORY of the system. All data survives app restarts.

Tables:
  - users: User profiles (each person gets their own portfolio)
  - portfolios: Each user's stock holdings (persists forever)
  - scan_cache: Last stock scan results (so data doesn't disappear on restart)
  - scan_meta: Metadata about when the last scan was run

Thread-safe: Uses connection-per-operation pattern with DELETE journal mode.
"""

import os
import json
import sqlite3
import datetime
import tempfile

DB_NAME = "bharat_ai_fund.db"
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

# Detect if the local repository directory is writeable (e.g. read-only on Streamlit Cloud mounts)
_is_writeable = False
try:
    _test_path = os.path.join(LOCAL_DIR, ".db_write_test")
    with open(_test_path, "w") as _f:
        _f.write("1")
    os.remove(_test_path)
    _is_writeable = True
except Exception:
    _is_writeable = False

import shutil

if _is_writeable:
    DB_PATH = os.path.join(LOCAL_DIR, DB_NAME)
else:
    # Fallback to writeable system temp folder for Streamlit Cloud
    DB_PATH = os.path.join(tempfile.gettempdir(), DB_NAME)
    # If the temp database does not exist, copy the pre-populated database from the git repo
    if not os.path.exists(DB_PATH):
        _repo_db_path = os.path.join(LOCAL_DIR, DB_NAME)
        if os.path.exists(_repo_db_path):
            try:
                shutil.copy2(_repo_db_path, DB_PATH)
                print(f"Copied pre-populated database from {_repo_db_path} to {DB_PATH}")
            except Exception as _e:
                print(f"Error copying pre-populated database: {_e}")



def get_connection():
    """
    Creates a new SQLite connection.
    Each operation opens/closes its own connection (thread-safe pattern).
    Uses DELETE journal mode to ensure compatibility with Linux container filesystems.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Creates all tables if they don't exist. Safe to call multiple times.
    Called once on app startup.
    """
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                email TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                buy_price REAL NOT NULL DEFAULT 0.0,
                quantity INTEGER NOT NULL DEFAULT 0,
                ltp REAL NOT NULL DEFAULT 0.0,
                sma_200 REAL NOT NULL DEFAULT 0.0,
                dist_pct REAL NOT NULL DEFAULT 0.0,
                above_sma INTEGER NOT NULL DEFAULT 0,
                signal TEXT NOT NULL DEFAULT 'WAIT',
                signal_strength INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT,
                _alert_emailed_date TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, symbol)
            );

            CREATE TABLE IF NOT EXISTS scan_cache (
                ticker TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS scan_meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_scan_time TEXT,
                total_stocks INTEGER DEFAULT 0,
                scan_mode TEXT DEFAULT 'Core 127'
            );

            -- Insert default scan_meta row if not exists
            INSERT OR IGNORE INTO scan_meta (id) VALUES (1);
        """)
        
        # Auto-migration: check if email column exists in users table, if not, add it
        try:
            conn.execute("SELECT email FROM users LIMIT 1")
        except sqlite3.OperationalError:
            print("Running migration: Adding 'email' column to 'users' table...")
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
            print("Migration successful.")
            
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# USER MANAGEMENT
# ---------------------------------------------------------------------------

def create_user(name, email=None):
    """
    Creates a new user profile. Returns the user_id.
    If user already exists, returns existing user_id.
    """
    conn = get_connection()
    try:
        # Check if exists
        row = conn.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
        if row:
            # Optionally update email if provided
            if email is not None:
                conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, row["id"]))
                conn.commit()
            return row["id"]
        
        cursor = conn.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_user_email(user_id, email):
    """Updates the email address of a user."""
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
        conn.commit()
    finally:
        conn.close()


def get_all_users():
    """Returns list of all user dicts: [{"id": 1, "name": "Gurjas", "email": "g@g.com"}, ...]"""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, name, email, created_at FROM users ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_user_by_name(name):
    """Returns user dict or None."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT id, name, email, created_at FROM users WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_user(user_id):
    """Deletes a user and all their portfolio holdings (CASCADE)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# PORTFOLIO CRUD (Multi-User)
# ---------------------------------------------------------------------------

def load_portfolio_db(user_id):
    """
    Loads all holdings for a specific user from SQLite.
    Returns list of holding dicts (same format as old portfolio.json).
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM portfolios WHERE user_id = ? ORDER BY symbol",
            (user_id,)
        ).fetchall()
        
        holdings = []
        for r in rows:
            holdings.append({
                "symbol": r["symbol"],
                "buy_price": r["buy_price"],
                "quantity": r["quantity"],
                "ltp": r["ltp"],
                "sma_200": r["sma_200"],
                "dist_pct": r["dist_pct"],
                "above_sma": bool(r["above_sma"]),
                "signal": r["signal"],
                "signal_strength": r["signal_strength"],
                "last_updated": r["last_updated"],
                "_alert_emailed_date": r["_alert_emailed_date"] or ""
            })
        return holdings
    finally:
        conn.close()


def save_portfolio_db(user_id, holdings):
    """
    Saves the entire portfolio for a user to SQLite.
    Uses INSERT OR REPLACE to handle updates.
    """
    conn = get_connection()
    try:
        # Clear existing holdings for this user and re-insert
        conn.execute("DELETE FROM portfolios WHERE user_id = ?", (user_id,))
        
        for h in holdings:
            conn.execute("""
                INSERT INTO portfolios 
                    (user_id, symbol, buy_price, quantity, ltp, sma_200, dist_pct, 
                     above_sma, signal, signal_strength, last_updated, _alert_emailed_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                h["symbol"],
                h["buy_price"],
                h["quantity"],
                h.get("ltp", 0.0),
                h.get("sma_200", 0.0),
                h.get("dist_pct", 0.0),
                1 if h.get("above_sma", False) else 0,
                h.get("signal", "WAIT"),
                h.get("signal_strength", 0),
                h.get("last_updated"),
                h.get("_alert_emailed_date", "")
            ))
        
        conn.commit()
    finally:
        conn.close()


def add_holding_db(user_id, symbol, buy_price, quantity):
    """
    Adds or updates a holding for a specific user.
    If symbol already exists for this user, updates price and quantity.
    Returns the updated holdings list.
    """
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM portfolios WHERE user_id = ? AND symbol = ?",
            (user_id, symbol)
        ).fetchone()
        
        if existing:
            conn.execute("""
                UPDATE portfolios SET buy_price = ?, quantity = ? 
                WHERE user_id = ? AND symbol = ?
            """, (buy_price, quantity, user_id, symbol))
        else:
            conn.execute("""
                INSERT INTO portfolios 
                    (user_id, symbol, buy_price, quantity, ltp, sma_200, dist_pct, 
                     above_sma, signal, signal_strength)
                VALUES (?, ?, ?, ?, 0.0, 0.0, 0.0, 0, 'WAIT', 0)
            """, (user_id, symbol, buy_price, quantity))
        
        conn.commit()
    finally:
        conn.close()
    
    return load_portfolio_db(user_id)


def remove_holding_db(user_id, symbol):
    """Removes a holding from a specific user's portfolio."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM portfolios WHERE user_id = ? AND symbol = ?",
            (user_id, symbol)
        )
        conn.commit()
    finally:
        conn.close()
    
    return load_portfolio_db(user_id)


def get_all_user_ids_with_portfolios():
    """Returns list of user_ids that have at least one holding. Used by scheduler."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT user_id FROM portfolios"
        ).fetchall()
        return [r["user_id"] for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# SCAN CACHE (Stock Data Persistence)
# ---------------------------------------------------------------------------

def save_scan_cache(stock_data_dict):
    """
    Saves stock scan results to SQLite for persistence across restarts.
    stock_data_dict: {ticker: {data_dict}} — same format as st.session_state["stock_cache"]
    
    NOTE: We serialize each stock's data to JSON. Large price arrays are included.
    """
    conn = get_connection()
    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        for ticker, data in stock_data_dict.items():
            # Convert data to JSON-serializable format
            serializable = _make_serializable(data)
            data_json = json.dumps(serializable)
            
            conn.execute("""
                INSERT OR REPLACE INTO scan_cache (ticker, data_json, updated_at)
                VALUES (?, ?, ?)
            """, (ticker, data_json, now_str))
        
        # Update scan metadata
        conn.execute("""
            UPDATE scan_meta SET last_scan_time = ?, total_stocks = ? WHERE id = 1
        """, (now_str, len(stock_data_dict)))
        
        conn.commit()
    finally:
        conn.close()


def load_scan_cache():
    """
    Loads stock scan results from SQLite.
    Returns: {ticker: {data_dict}} — same format as st.session_state["stock_cache"]
    Returns empty dict if no cached data.
    """
    conn = get_connection()
    try:
        rows = conn.execute("SELECT ticker, data_json FROM scan_cache").fetchall()
        
        result = {}
        for r in rows:
            try:
                data = json.loads(r["data_json"])
                result[r["ticker"]] = data
            except json.JSONDecodeError:
                continue
        
        return result
    finally:
        conn.close()


def get_scan_meta():
    """Returns scan metadata: last_scan_time, total_stocks, scan_mode."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM scan_meta WHERE id = 1").fetchone()
        if row:
            return dict(row)
        return {"last_scan_time": None, "total_stocks": 0, "scan_mode": "Core 127"}
    finally:
        conn.close()


def clear_scan_cache():
    """Clears all scan cache data. Used when switching universe modes."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM scan_cache")
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# MIGRATION: Import existing portfolio.json into SQLite
# ---------------------------------------------------------------------------

def migrate_from_json(json_path="portfolio.json", default_user_name="Gurjas"):
    """
    One-time migration: imports existing portfolio.json into SQLite under a default user.
    Safe to call multiple times — skips if user already has holdings.
    Returns True if migration happened, False if skipped.
    """
    if not os.path.exists(json_path):
        return False
    
    try:
        with open(json_path, "r") as f:
            old_holdings = json.load(f)
        
        if not old_holdings or not isinstance(old_holdings, list):
            return False
        
        # Create or get default user
        user_id = create_user(default_user_name)
        
        # Check if user already has holdings (don't overwrite)
        existing = load_portfolio_db(user_id)
        if existing:
            return False
        
        # Migrate
        save_portfolio_db(user_id, old_holdings)
        print(f"✅ Migrated {len(old_holdings)} holdings from portfolio.json to SQLite (user: {default_user_name})")
        return True
        
    except Exception as e:
        print(f"Migration error: {e}")
        return False


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _make_serializable(data):
    """Converts a stock data dict to JSON-serializable format (handles datetime, etc.)."""
    serializable = {}
    for k, v in data.items():
        if isinstance(v, datetime.datetime):
            serializable[k] = v.isoformat()
        elif isinstance(v, (list, dict, str, int, float, bool, type(None))):
            serializable[k] = v
        else:
            serializable[k] = str(v)
    return serializable


# ---------------------------------------------------------------------------
# INIT: Run on import
# ---------------------------------------------------------------------------
init_db()
