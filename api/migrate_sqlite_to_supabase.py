"""
migrate_sqlite_to_supabase.py — One-Time Data Migration Script
                                Phase 1 / Brick 1.4

Reads ALL data from bharat_ai_fund.db (SQLite)
and pushes it to Supabase (PostgreSQL).

Run ONCE after Supabase project is set up and .env has credentials.

Usage:
    python migrate_sqlite_to_supabase.py

What it migrates:
    1. users           — all user profiles
    2. portfolios      — all holdings (for all users)
    3. scan_cache      — 1,448 pre-populated stock records
    4. scan_meta       — last scan timestamp
    5. portfolio_store.json — fallback if DB is empty

Safety:
    - Non-destructive: never deletes local SQLite data
    - Idempotent: safe to run multiple times (upserts, not inserts)
    - Prints row-by-row progress and final verification counts
"""

import os
import sys
import json
import sqlite3
import datetime

# ── Make sure .env is loaded before supabase_db imports ──────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── Local imports ─────────────────────────────────────────────────────────────
import db as sqlite_db              # existing SQLite module
import supabase_db as supa          # new Supabase module


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_section(title: str):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

def print_step(msg: str):
    print(f"\n[MIGRATE] {msg}")

def print_ok(msg: str):
    print(f"   [OK] {msg}")

def print_warn(msg: str):
    print(f"   [WARN] {msg}")

def print_info(msg: str):
    print(f"   [INFO] {msg}")


# ---------------------------------------------------------------------------
# STEP 1: MIGRATE USERS
# ---------------------------------------------------------------------------

def migrate_users() -> dict[str, int]:
    print_section("STEP 1 -- Migrating Users")
    id_map = {}   # sqlite_id -> supabase_id

    sqlite_users = sqlite_db.get_all_users()
    print_info(f"Found {len(sqlite_users)} user(s) in SQLite")

    for u in sqlite_users:
        supa_id = supa.create_user(name=u["name"], email=u.get("email"))
        id_map[u["id"]] = supa_id
        print_ok(f"User '{u['name']}' --> Supabase id={supa_id}")

    return id_map


def migrate_portfolios(id_map: dict[str, int]):
    print_section("STEP 2 -- Migrating Portfolios")

    for sqlite_uid, supa_uid in id_map.items():
        holdings = sqlite_db.load_portfolio_db(sqlite_uid)
        if not holdings:
            print_warn(f"User sqlite_id={sqlite_uid} has no holdings -- skipping")
            continue

        supa.save_portfolio_db(supa_uid, holdings)
        print_ok(f"Migrated {len(holdings)} holdings for sqlite_id={sqlite_uid} --> supa_id={supa_uid}")

    if os.path.exists("portfolio_store.json"):
        print_info("Found portfolio_store.json -- running JSON migration fallback...")
        supa.migrate_from_json("portfolio_store.json")


# ---------------------------------------------------------------------------
# STEP 3: MIGRATE SCAN CACHE
# ---------------------------------------------------------------------------

def migrate_scan_cache():
    print_section("STEP 3 -- Migrating Scan Cache")
    print_info("This may take 30-60 seconds for large caches...")

    cache = sqlite_db.load_scan_cache()
    if not cache:
        print_warn("No scan cache data found in SQLite -- skipping")
        return

    print_info(f"Loaded {len(cache)} stocks from SQLite scan_cache")
    supa.save_scan_cache(cache)
    print_ok(f"Migrated {len(cache)} stocks to Supabase scan_cache")


def migrate_scan_meta():
    print_section("STEP 4 -- Migrating Scan Meta")

    meta = sqlite_db.get_scan_meta()
    print_info(f"SQLite scan_meta: {meta}")

    supa._upsert("scan_meta", {
        "id":            1,
        "last_scan_time": meta.get("last_scan_time"),
        "total_stocks":   meta.get("total_stocks", 0),
        "scan_mode":      meta.get("scan_mode", "Core 127"),
    }, on_conflict="id")

    print_ok(f"Scan meta migrated: last_scan={meta.get('last_scan_time')}, stocks={meta.get('total_stocks')}")


def verify_migration(id_map: dict[str, int]):
    print_section("STEP 5 -- Verification")

    sqlite_users = sqlite_db.get_all_users()
    supa_users   = supa.get_all_users()
    status = "[OK]" if len(supa_users) >= len(sqlite_users) else "[FAIL]"
    print(f"  {status}  Users:     SQLite={len(sqlite_users)}  -->  Supabase={len(supa_users)}")

    # Scan cache
    sqlite_cache = sqlite_db.load_scan_cache()
    supa_cache = supa.load_scan_cache()
    supa_count = len(supa_cache)
    status = "[OK]" if supa_count >= len(sqlite_cache) else "[WARN]"
    print(f"  {status}  Scan cache: SQLite={len(sqlite_cache)}  -->  Supabase={supa_count}")

    # Portfolios
    total_sqlite_holdings = sum(len(sqlite_db.load_portfolio_db(uid)) for uid in id_map.keys())
    total_supa_holdings   = sum(len(supa.load_portfolio_db(suid)) for suid in id_map.values())
    status = "[OK]" if total_supa_holdings >= total_sqlite_holdings else "[WARN]"
    print(f"  {status}  Holdings:  SQLite={total_sqlite_holdings}  -->  Supabase={total_supa_holdings}")

    print_section("Migration Complete!")
    if total_supa_holdings >= total_sqlite_holdings and supa_count >= len(sqlite_cache):
        print("  [SUCCESS] All data successfully migrated to Supabase!")
        print("  Next: Update .env with SUPABASE_URL and SUPABASE_SERVICE_KEY")
        print("        Then swap  'import db'  →  'import supabase_db as db'  in other files")
    else:
        print("  ⚠️  Some counts don't match. Check errors above and re-run.")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("\n" + "="*60)
    print("  BHARAT AI FUND MANAGER -- SQLite to Supabase Migration")
    print(f"  Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Confirm Supabase is reachable
    try:
        supa._require_config()
        supa._get("scan_meta", {"select": "id", "limit": "1"})
        print_ok("Supabase connection verified")
    except Exception as e:
        print(f"\n[ERROR] Cannot connect to Supabase: {e}")
        print("   --> Check SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env file")
        sys.exit(1)

    # Run migration steps
    id_map = migrate_users()
    migrate_portfolios(id_map)
    migrate_scan_cache()
    migrate_scan_meta()
    verify_migration(id_map)


if __name__ == "__main__":
    main()
