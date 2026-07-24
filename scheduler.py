"""
scheduler.py — Automated Scheduler for Bharat AI Fund Manager Gill

UPGRADED: Now supports --market-schedule mode for automatic twice-daily operation.

Modes:
  --now               : Run scan + portfolio sync immediately and exit
  --sync-portfolio    : Only sync portfolio prices (all users) and send alerts
  --market-schedule   : Run at 10:00 AM + 4:00 PM IST daily (for Windows Task Scheduler)
  --twice-daily       : Legacy polling mode (checks every 30 min)
  --interval N        : Run every N days

Portfolio sync now refreshes ALL users' portfolios (multi-user aware).
"""

import os
import sys
import time
import datetime
import argparse
from dotenv import load_dotenv

from symbols import get_all_tickers
from data_fetcher import (
    batch_update_stocks, batch_update_stocks_parallel,
    save_scan_results_to_db
)
from scoring_engine import run_scoring
from report_generator import generate_excel_report, generate_pdf_report
from email_dispatcher import send_momentum_newsletter
from portfolio_manager import (
    load_portfolio, save_portfolio, update_portfolio_prices,
    send_alert_email, check_and_trigger_alerts
)
from db import (
    get_all_user_ids_with_portfolios, get_all_users,
    load_portfolio_db, save_portfolio_db
)

load_dotenv()

def execute_portfolio_sync():
    """
    Refreshes portfolio prices for ALL users and triggers email alerts.
    Multi-user aware — iterates through every user who has portfolio holdings.
    """
    user_ids = get_all_user_ids_with_portfolios()
    
    if not user_ids:
        print("No users with portfolios found — skipping portfolio sync.")
        return
    
    all_users = {u["id"]: (u["name"], u.get("email")) for u in get_all_users()}
    
    for uid in user_ids:
        user_name, user_email = all_users.get(uid, (f"User #{uid}", None))
        portfolio = load_portfolio_db(uid)
        
        if not portfolio:
            continue
        
        print(f"\n📊 Syncing portfolio for '{user_name}' ({len(portfolio)} holdings)...")
        portfolio = update_portfolio_prices(portfolio, user_id=uid)
        
        # Check for stocks below 200 SMA and send email alerts
        below_sma = [h for h in portfolio if h.get("sma_200", 0) > 0 and not h.get("above_sma", False)]
        if below_sma:
            print(f"  ⚠️  {len(below_sma)} stock(s) BELOW 200 SMA for {user_name}! Sending alerts...")
            for h in below_sma:
                sym = h["symbol"].replace(".NS", "")
                ltp = h["ltp"]
                sma = h["sma_200"]
                dist = h["dist_pct"]
                print(f"    🚨 {sym}: LTP=₹{ltp}, 200 SMA=₹{sma}, Distance={dist}%")
                
                # Email alert (once per day per stock)
                already_emailed = h.get("_alert_emailed_date", "")
                today_str = datetime.datetime.now().strftime("%Y-%m-%d")
                if already_emailed != today_str:
                    send_alert_email(h, user_name=user_name, user_email=user_email)
                    h["_alert_emailed_date"] = today_str
            
            # Save updated alert dates
            save_portfolio_db(uid, portfolio)
        else:
            print(f"  ✅ All holdings above 200 SMA for {user_name}")
    
    print("\n✅ Portfolio sync complete for all users.")

def execute_scan_and_report(universe_size=None):
    """
    Runs full stock scan and generates reports.
    Saves scan results to SQLite for persistence.
    """
    print(f"[{datetime.datetime.now()}] Starting automated scan for Bharat AI Fund Manager...")
    
    # Determine universe
    if universe_size and universe_size > 0:
        tickers = get_all_tickers(use_full=True, limit=universe_size)
    else:
        tickers = get_all_tickers(use_full=True)
    
    print(f"Updating data cache for {len(tickers)} stocks...")
    
    # Use parallel fetcher for large universes
    if len(tickers) > 200:
        data = batch_update_stocks_parallel(tickers, force_refresh=True, max_workers=10)
    else:
        data = batch_update_stocks(tickers, force_refresh=True)
    
    # Save scan results to SQLite for persistence
    if data:
        save_scan_results_to_db(data)
        print(f"💾 Scan results persisted to SQLite ({len(data)} stocks)")
    
    print("Running scoring engine...")
    df, latest_highs, continuous, red_alerts = run_scoring(data)
    
    if df.empty:
        print("Error: Scored dataset is empty. Check internet connectivity.")
        return False
        
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    pdf_name = f"Bharat_AI_Gill_Momentum_Report_{date_str}.pdf"
    excel_name = f"Bharat_AI_Gill_Momentum_Data_{date_str}.xlsx"
    pdf_path = os.path.join("reports", pdf_name)
    excel_path = os.path.join("reports", excel_name)
    os.makedirs("reports", exist_ok=True)
    
    print("Generating report files...")
    pdf_ok = generate_pdf_report(df, pdf_name)
    excel_ok = generate_excel_report(df, latest_highs, continuous, red_alerts, excel_name)
    
    if pdf_ok and excel_ok:
        print(f"Reports generated successfully:\n- {pdf_path}\n- {excel_path}")
        
        run_date_nice = datetime.datetime.now().strftime("%d %B %Y")
        mail_ok, mail_msg = send_momentum_newsletter(pdf_path, excel_path, run_date_nice)
        if mail_ok:
            print("Newsletter dispatched successfully!")
        else:
            print(f"Newsletter skip/failure: {mail_msg}")
        return True
    else:
        print("Error: Report generation failed.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Bharat AI Fund Manager automated scheduler")
    parser.add_argument("--now", action="store_true", help="Run scan and portfolio sync immediately and exit")
    parser.add_argument("--interval", type=int, default=7, help="Loop interval in days (default: 7)")
    parser.add_argument("--sync-portfolio", action="store_true", help="Only sync portfolio prices and alerts for ALL users (no full scan)")
    parser.add_argument("--twice-daily", action="store_true", help="Legacy: Run in twice-daily polling mode")
    parser.add_argument("--market-schedule", action="store_true", 
                        help="Run at market hours: 10 AM + 4 PM IST. Designed for Windows Task Scheduler.")
    parser.add_argument("--universe", type=int, default=0, help="Stock universe size (0=Core 127, 500, 1000, 2000, 3000)")
    parser.add_argument("--auto-clean", type=int, default=0, help="Auto-delete cache older than N days before scan (default: 0 = off)")
    args = parser.parse_args()
    
    # Auto-clean old cache if requested
    if args.auto_clean > 0:
        import shutil
        cache_dirs = ["data_cache", "screener_cache", "reports"]
        for d in cache_dirs:
            if os.path.exists(d):
                now_ts = time.time()
                deleted = 0
                for fname in os.listdir(d):
                    fpath = os.path.join(d, fname)
                    if os.path.isfile(fpath):
                        age_days = (now_ts - os.path.getmtime(fpath)) / 86400
                        if age_days > args.auto_clean:
                            os.remove(fpath)
                            deleted += 1
                if deleted > 0:
                    print(f"🧹 Cleaned {deleted} old files from {d}/ (>{args.auto_clean}d)")
    
    if args.sync_portfolio:
        execute_portfolio_sync()
        sys.exit(0)
    
    if args.now:
        execute_scan_and_report(universe_size=args.universe if args.universe > 0 else None)
        # Also sync portfolios for all users
        execute_portfolio_sync()
        sys.exit(0)
    
    if args.market_schedule:
        # ============================================================
        # MARKET SCHEDULE MODE — Designed for Windows Task Scheduler
        # Runs ONCE: scan + portfolio sync, then exits.
        # Task Scheduler handles calling it at 10 AM + 4 PM.
        # ============================================================
        now = datetime.datetime.now()
        print("=" * 60)
        print("BHARAT AI SCHEDULER — MARKET SCHEDULE MODE")
        print(f"Triggered at: {now.strftime('%Y-%m-%d %H:%M:%S IST')}")
        print(f"Universe: {args.universe if args.universe > 0 else 'Core 127'}")
        print("=" * 60)
        
        execute_scan_and_report(universe_size=args.universe if args.universe > 0 else None)
        execute_portfolio_sync()
        
        print(f"\n{'=' * 60}")
        print(f"✅ Market schedule run complete at {datetime.datetime.now().strftime('%H:%M:%S')}")
        print(f"Next run will be triggered by Windows Task Scheduler.")
        print(f"{'=' * 60}")
        sys.exit(0)
    
    if args.twice_daily:
        print("=" * 60)
        print("BHARAT AI SCHEDULER — TWICE DAILY MODE (Legacy Polling)")
        print(f"Started at: {datetime.datetime.now()}")
        print("Schedule: Morning (~10:00) + Evening (~16:00)")
        print("=" * 60)
        while True:
            now = datetime.datetime.now()
            hour = now.hour
            minute = now.minute
            
            # Morning run: 10:00-10:30 AM IST
            # Evening run: 16:00-16:30 PM IST
            if (hour == 10 and minute < 30) or (hour == 16 and minute < 30):
                print(f"\n[{now}] Scheduled run triggered...")
                execute_scan_and_report(universe_size=args.universe if args.universe > 0 else None)
                execute_portfolio_sync()
                # Sleep extra to avoid re-running in same window
                time.sleep(3600)  # 1 hour
            else:
                # Sleep 30 minutes before checking again
                print(f"[{datetime.datetime.now()}] Waiting... next check in 30 min", end="\r")
                time.sleep(1800)
    
    print(f"Bharat AI Scheduler service started. Scanning every {args.interval} days...")
    print("Portfolio will be synced for ALL users on each run.")
    while True:
        execute_scan_and_report(universe_size=args.universe if args.universe > 0 else None)
        execute_portfolio_sync()
        print(f"Scan complete. Sleeping for {args.interval} days...")
        time.sleep(args.interval * 86400)

if __name__ == "__main__":
    main()
