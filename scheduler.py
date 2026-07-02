import os
import sys
import time
import datetime
import argparse
from dotenv import load_dotenv

from symbols import get_all_tickers
from data_fetcher import batch_update_stocks
from scoring_engine import run_scoring
from report_generator import generate_excel_report, generate_pdf_report
from email_dispatcher import send_momentum_newsletter
from portfolio_manager import load_portfolio, save_portfolio, update_portfolio_prices, send_alert_email

load_dotenv()

def execute_portfolio_sync():
    """
    Refreshes portfolio prices and triggers email alerts for stocks below 200 SMA.
    This is the daily portfolio check that runs alongside the main scan.
    """
    portfolio = load_portfolio()
    if not portfolio:
        print("Portfolio is empty — skipping portfolio sync.")
        return
    
    print(f"Refreshing prices for {len(portfolio)} portfolio holdings...")
    portfolio = update_portfolio_prices(portfolio)
    
    # Check for stocks below 200 SMA and send email alerts
    below_sma = [h for h in portfolio if h.get("sma_200", 0) > 0 and not h.get("above_sma", False)]
    if below_sma:
        print(f"⚠️  {len(below_sma)} stock(s) are BELOW 200 SMA! Sending email alerts...")
        for h in below_sma:
            sym = h["symbol"].replace(".NS", "")
            ltp = h["ltp"]
            sma = h["sma_200"]
            dist = h["dist_pct"]
            print(f"  🚨 {sym}: LTP=₹{ltp}, 200 SMA=₹{sma}, Distance={dist}%")
            send_alert_email(h)
    else:
        print("✅ All portfolio holdings are above 200 SMA — no alerts needed.")
    
    save_portfolio(portfolio)
    print("Portfolio sync complete.")

def execute_scan_and_report():
    print(f"[{datetime.datetime.now()}] Starting automated scan for Bharat AI Fund Manager...")
    tickers = get_all_tickers()
    
    print(f"Updating data cache for {len(tickers)} stocks...")
    data = batch_update_stocks(tickers, force_refresh=True)
    
    print("Running scoring engine...")
    df, latest_highs, continuous, red_alerts = run_scoring(data)
    
    if df.empty:
        print("Error: Scored dataset is empty. Check internet connectivity.")
        return False
        
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    pdf_path = f"Bharat_AI_Gill_Momentum_Report_{date_str}.pdf"
    excel_path = f"Bharat_AI_Gill_Momentum_Data_{date_str}.xlsx"
    
    print("Generating report files...")
    pdf_ok = generate_pdf_report(df, pdf_path)
    excel_ok = generate_excel_report(df, latest_highs, continuous, red_alerts, excel_path)
    
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
    parser.add_argument("--sync-portfolio", action="store_true", help="Only sync portfolio prices and alerts (no full scan)")
    args = parser.parse_args()
    
    if args.sync_portfolio:
        execute_portfolio_sync()
        sys.exit(0)
    
    if args.now:
        execute_scan_and_report()
        # Also sync portfolio
        execute_portfolio_sync()
        sys.exit(0)
        
    print(f"Bharat AI Scheduler service started. Scanning every {args.interval} days...")
    print("Portfolio will be synced on each run.")
    while True:
        execute_scan_and_report()
        execute_portfolio_sync()
        print(f"Scan complete. Sleeping for {args.interval} days...")
        time.sleep(args.interval * 86400)

if __name__ == "__main__":
    main()
