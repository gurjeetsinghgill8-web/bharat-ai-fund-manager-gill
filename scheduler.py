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

load_dotenv()

def execute_scan_and_report():
    print(f"[{datetime.datetime.now()}] Starting automated scan for Bharat AI Fund Manager...")
    tickers = get_all_tickers()
    
    print(f"Updating data cache for {len(tickers)} stocks...")
    # Fetch/update cache
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
        
        # Check SMTP settings and dispatch
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
    parser.add_argument("--now", action="store_true", help="Run scan immediately and exit")
    parser.add_argument("--interval", type=int, default=7, help="Loop interval in days (default: 7)")
    args = parser.parse_args()
    
    if args.now:
        execute_scan_and_report()
        sys.exit(0)
        
    print(f"Bharat AI Scheduler service started. Scanning every {args.interval} days...")
    while True:
        execute_scan_and_report()
        print(f"Scan complete. Sleeping for {args.interval} days...")
        time.sleep(args.interval * 86400) # days in seconds

if __name__ == "__main__":
    main()
