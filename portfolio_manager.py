"""
portfolio_manager.py — Multi-User Portfolio Manager with SQLite Persistence

UPGRADED from single-user portfolio.json to multi-user SQLite.
Every function now takes user_id to isolate portfolios per person.

Key changes from v1:
  - load_portfolio(user_id) → loads ONLY that user's stocks from SQLite
  - save_portfolio(user_id, holdings) → saves to SQLite (permanent)
  - add_holding(user_id, symbol, buy_price, quantity) → per-user
  - remove_holding(user_id, symbol) → per-user
  - All alert/export functions are user-scoped
"""

import os
import json
import datetime
import yfinance as yf
import pandas as pd

from db import (
    load_portfolio_db, save_portfolio_db, add_holding_db, remove_holding_db,
    get_all_user_ids_with_portfolios, get_all_users
)

# Legacy file path — kept for migration only
PORTFOLIO_FILE = "portfolio.json"

# ---------------------------------------------------------------------------
# Portfolio CRUD (SQLite-backed, multi-user)
# ---------------------------------------------------------------------------

def load_portfolio(user_id=None):
    """
    Loads a user's portfolio from SQLite.
    Returns a list of holding dicts, or an empty list if none exist.
    Each holding:
    {
        "symbol": "RELIANCE.NS",
        "buy_price": 2500.0,
        "quantity": 10,
        "ltp": 0.0,
        "sma_200": 0.0,
        "dist_pct": 0.0,
        "above_sma": False,
        "signal": "WAIT",
        "last_updated": None
    }
    """
    if user_id is None:
        return []
    return load_portfolio_db(user_id)


def save_portfolio(holdings, user_id=None):
    """Saves the portfolio to SQLite for a specific user."""
    if user_id is None:
        return
    save_portfolio_db(user_id, holdings)


def add_holding(symbol, buy_price, quantity, user_id=None):
    """
    Adds a new holding to the user's portfolio.
    If the symbol already exists for this user, updates the existing entry.
    """
    if user_id is None:
        return []
    return add_holding_db(user_id, symbol, buy_price, quantity)


def remove_holding(symbol, user_id=None):
    """Removes a holding from the user's portfolio by symbol."""
    if user_id is None:
        return []
    return remove_holding_db(user_id, symbol)


# ---------------------------------------------------------------------------
# Lightweight price + SMA fetcher (no financials – fast)
# ---------------------------------------------------------------------------

def fetch_ltp_and_sma(ticker):
    """
    Lightweight fetch: gets current price and 200-day SMA for a ticker.
    Uses only ~1 year of price history (no financial statements).
    
    Returns:
        (ltp, sma_200) or (None, None) on failure.
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if hist.empty:
            hist = t.history(period="6mo")
        if hist.empty:
            return None, None
        
        ltp = float(hist['Close'].iloc[-1])
        
        sma_200 = 0.0
        if len(hist) >= 200:
            sma_200 = float(hist['Close'].rolling(window=200).mean().iloc[-1])
        elif not hist.empty:
            sma_200 = float(hist['Close'].mean())
        
        return ltp, sma_200
    except Exception as e:
        print(f"Error fetching LTP/SMA for {ticker}: {str(e)}")
        return None, None

def generate_portfolio_signals(holdings):
    """
    Computes an auto-trade signal for each holding.
    
    Signal Logic:
      - EXIT  → below 200 SMA (immediate exit required)
      - BUY   → above 200 SMA, distance < 15% (good entry zone, close to MA)
      - HOLD  → above 200 SMA, distance >= 15% (already run up, hold for more)
      - WAIT  → no SMA data yet
    
    Also sets signal_strength: 1 (weak) to 5 (strong)
    
    Modifies holdings in-place and returns them.
    """
    for h in holdings:
        sma = h.get("sma_200", 0)
        above = h.get("above_sma", False)
        dist = h.get("dist_pct", 0)
        
        if sma <= 0:
            h["signal"] = "WAIT"
            h["signal_strength"] = 0
        elif not above:
            h["signal"] = "EXIT"
            # Strength: how far below — worse = stronger signal
            h["signal_strength"] = min(5, max(1, int(abs(dist) / 2)))
        elif dist < 15:
            h["signal"] = "BUY"
            h["signal_strength"] = 5 - int(dist / 3)  # closer = stronger
        else:
            h["signal"] = "HOLD"
            h["signal_strength"] = 3  # neutral
    
    return holdings

def update_portfolio_prices(holdings, user_id=None):
    """
    Iterates over all holdings and fetches fresh LTP + 200 SMA for each.
    Updates ltp, sma_200, dist_pct, above_sma, signal, and last_updated in-place.
    Auto-saves to SQLite after update.
    
    Returns the updated list.
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    for h in holdings:
        sym = h["symbol"]
        ltp, sma = fetch_ltp_and_sma(sym)
        if ltp is not None:
            h["ltp"] = round(ltp, 2)
            h["sma_200"] = round(sma, 2) if sma else 0.0
            h["last_updated"] = now_str
            
            if sma > 0:
                h["dist_pct"] = round(((ltp - sma) / sma) * 100.0, 2)
                h["above_sma"] = ltp >= sma
            else:
                h["dist_pct"] = 0.0
                h["above_sma"] = True  # If no SMA data, assume pass
    
    # Generate signals after prices update
    holdings = generate_portfolio_signals(holdings)
    
    # Save to SQLite (persistent!)
    if user_id is not None:
        save_portfolio(holdings, user_id=user_id)
    
    return holdings

# ---------------------------------------------------------------------------
# Alert Systems (Sound + Desktop Notification + Email)
# ---------------------------------------------------------------------------

def play_alert_sound(repeat=3):
    """
    Plays a loud repeating beep sound using Windows built-in winsound.
    This is the 🔊 SIREN ALERT when a stock goes below 200 SMA.
    """
    try:
        import winsound
        for i in range(repeat):
            winsound.Beep(1000, 500)   # 1000 Hz, 500ms — loud beep
            winsound.Beep(1200, 500)   # higher pitch for urgency
            winsound.Beep(800, 500)    # lower pitch — siren effect
            if i < repeat - 1:
                import time
                time.sleep(0.2)
    except Exception as e:
        print(f"Alert sound error: {e}")

def show_desktop_notification(title, message):
    """
    Shows a Windows 10 toast notification using win10toast library.
    This is the 📢 Desktop Notification alert.
    """
    try:
        from win10toast import ToastNotifier
        n = ToastNotifier()
        n.show_toast(
            title,
            message,
            duration=10,
            threaded=True
        )
    except ImportError:
        print("win10toast not installed. Run: pip install win10toast")
    except Exception as e:
        print(f"Desktop notification error: {e}")

def send_alert_email(holding, user_name="", user_email=None):
    """
    Sends an instant alert email when a stock breaches below 200 SMA.
    Uses SMTP config from environment variables (same as email_dispatcher.py).
    If user_email is provided, sends directly to them. Otherwise falls back to EMAIL_RECIPIENTS.
    """
    try:
        import smtplib
        from email.message import EmailMessage
        
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")
        
        # Use user-specific email if available, otherwise global config
        recipients = user_email if user_email else os.getenv("EMAIL_RECIPIENTS", "")
        
        if not smtp_user or not smtp_pass or not recipients:
            print("Email alert skipped: SMTP or recipients not configured")
            return False
        
        sym = holding["symbol"].replace(".NS", "")
        ltp = holding["ltp"]
        sma = holding["sma_200"]
        dist = holding["dist_pct"]
        buy_price = holding["buy_price"]
        qty = holding["quantity"]
        pl_pct = round(((ltp - buy_price) / buy_price) * 100, 2)
        
        user_tag = f" [{user_name}]" if user_name else ""
        
        msg = EmailMessage()
        msg.set_content(f"""
🚨🚨 BHARAT AI FUND MANAGER - CRITICAL ALERT{user_tag} 🚨🚨

⚠️ {sym} has fallen BELOW its 200-day SMA!

Portfolio Owner: {user_name or 'Default'}
Current Price:  ₹{ltp}
200 SMA:       ₹{sma}
Distance:      {dist}%
Your Buy:      ₹{buy_price} × {qty} shares
Your P&L:      {pl_pct}%

🚨 RECOMMENDATION: EXIT IMMEDIATELY!
The stock is trading below its long-term moving average.
This is a strong signal that the trend has turned bearish.

— Jarvis Auto Alert System
        """)
        
        msg["Subject"] = f"🚨 CRITICAL{user_tag}: {sym} BELOW 200 SMA — EXIT NOW!"
        msg["From"] = smtp_user
        msg["To"] = recipients
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        print(f"Alert email sent for {sym} to {recipients} (user: {user_name})")
        return True
        
    except Exception as e:
        print(f"Error sending alert email: {e}")
        return False

def check_and_trigger_alerts(holdings, user_name="", user_email=None):
    """
    Master alert trigger: checks all holdings and fires ALL alert types
    for any stock that is below 200 SMA.
    
    Returns the list of stocks that triggered alerts (for display).
    """
    below_sma = [h for h in holdings if h.get("sma_200", 0) > 0 and not h.get("above_sma", False)]
    
    if below_sma:
        # 🔊 Sound alert
        play_alert_sound(repeat=3)
        
        for h in below_sma:
            sym = h["symbol"].replace(".NS", "")
            ltp = h["ltp"]
            sma = h["sma_200"]
            dist = h["dist_pct"]
            
            # 📢 Desktop notification
            show_desktop_notification(
                f"🚨 {sym} BELOW 200 SMA!",
                f"LTP: ₹{ltp} | 200 SMA: ₹{sma} | Distance: {dist}%\nEXIT IMMEDIATELY!"
            )
            
            # 📧 Email alert (only once per symbol per day to avoid spam)
            already_emailed_today = h.get("_alert_emailed_date", "")
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            if already_emailed_today != today_str:
                send_alert_email(h, user_name=user_name, user_email=user_email)
                h["_alert_emailed_date"] = today_str
    
    return below_sma

# ---------------------------------------------------------------------------
# Excel Export for Portfolio
# ---------------------------------------------------------------------------

def export_portfolio_to_excel(holdings, filename="portfolio_report.xlsx"):
    """
    Exports the portfolio to a professionally formatted Excel file.
    Uses xlsxwriter for formatting (already installed).
    
    Returns True on success, False on failure.
    """
    try:
        if not holdings:
            return False
        
        # Build a clean DataFrame
        rows = []
        for h in holdings:
            sym = h["symbol"].replace(".NS", "")
            buy = h["buy_price"]
            qty = h["quantity"]
            invested = round(buy * qty, 2)
            ltp = h["ltp"]
            curr_val = round(ltp * qty, 2) if ltp > 0 else 0
            pl_pct = round(((ltp - buy) / buy) * 100, 2) if ltp > 0 and buy > 0 else 0
            sma = h["sma_200"]
            dist = h["dist_pct"]
            above = h.get("above_sma", False)
            signal = h.get("signal", "WAIT")
            updated = h.get("last_updated", "")
            
            rows.append({
                "Symbol": sym,
                "Buy Price": buy,
                "Quantity": qty,
                "Invested": invested,
                "LTP": ltp if ltp > 0 else 0,
                "Current Value": curr_val,
                "P&L %": pl_pct,
                "200 SMA": sma if sma > 0 else 0,
                "SMA Dist %": dist,
                "Above SMA": "YES" if above else "NO",
                "Signal": signal,
                "Last Updated": updated
            })
        
        df = pd.DataFrame(rows)
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='My Portfolio', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['My Portfolio']
            
            # Formats
            header_fmt = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#0B192C',
                'font_color': '#FFFFFF',
                'border': 1,
                'font_size': 11
            })
            
            green_fmt = workbook.add_format({
                'fg_color': '#D5F5E3',
                'border': 1,
                'num_format': '#,##0.00'
            })
            
            red_fmt = workbook.add_format({
                'fg_color': '#FADBD8',
                'border': 1,
                'num_format': '#,##0.00'
            })
            
            money_fmt = workbook.add_format({
                'num_format': '₹#,##0.00',
                'border': 1
            })
            
            pct_fmt = workbook.add_format({
                'num_format': '0.00%',
                'border': 1
            })
            
            # Write formatted headers
            for col_num, col_name in enumerate(df.columns):
                worksheet.write(0, col_num, col_name, header_fmt)
                # Auto-fit columns
                worksheet.set_column(col_num, col_num, max(len(str(col_name)) + 4, 14))
            
            # Apply conditional formatting and styling
            above_sma_col = df.columns.get_loc("Above SMA")
            signal_col = df.columns.get_loc("Signal")
            
            for row_num in range(1, len(df) + 1):
                is_above = df.iloc[row_num - 1]["Above SMA"] == "YES"
                signal_val = df.iloc[row_num - 1]["Signal"]
                
                row_fmt = green_fmt if is_above else red_fmt
                
                # Apply row background color
                for col_num in range(len(df.columns)):
                    worksheet.write(row_num, col_num, df.iloc[row_num - 1, col_num], row_fmt)
                
                # Override signal column with colored text
                if signal_val == "EXIT":
                    signal_fmt = workbook.add_format({
                        'bold': True,
                        'font_color': '#FF0000',
                        'fg_color': '#FADBD8',
                        'border': 1
                    })
                    worksheet.write(row_num, signal_col, "🚨 EXIT", signal_fmt)
                elif signal_val == "BUY":
                    signal_fmt = workbook.add_format({
                        'bold': True,
                        'font_color': '#006600',
                        'fg_color': '#D5F5E3',
                        'border': 1
                    })
                    worksheet.write(row_num, signal_col, "✅ BUY", signal_fmt)
                elif signal_val == "HOLD":
                    signal_fmt = workbook.add_format({
                        'bold': True,
                        'font_color': '#CC8800',
                        'fg_color': '#FEF9E7',
                        'border': 1
                    })
                    worksheet.write(row_num, signal_col, "✅ HOLD", signal_fmt)
            
            # Freeze header row
            worksheet.freeze_panes(1, 0)
        
        return True
        
    except Exception as e:
        print(f"Error exporting portfolio to Excel: {e}")
        return False

# ---------------------------------------------------------------------------
# Portfolio Share/Import (JSON for email-sharing)
# ---------------------------------------------------------------------------

def export_portfolio_to_json(holdings, filename="portfolio_share.json"):
    """
    Exports the portfolio to a shareable JSON file.
    Returns the file path on success, None on failure.
    Can be attached to email for sharing between users.
    """
    try:
        import os
        # Save to reports/ directory
        os.makedirs("reports", exist_ok=True)
        filepath = os.path.join("reports", filename)
        
        with open(filepath, "w") as f:
            json.dump(holdings, f, indent=2)
        print(f"Portfolio exported to {filepath}")
        return filepath
    except Exception as e:
        print(f"Error exporting portfolio to JSON: {e}")
        return None

def import_portfolio_from_json(filepath):
    """
    Imports a portfolio from a JSON file.
    Returns the list of holdings on success, None on failure.
    """
    try:
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return None
        with open(filepath, "r") as f:
            holdings = json.load(f)
        # Validate structure
        if not isinstance(holdings, list):
            print("Invalid portfolio format: expected a list")
            return None
        required_keys = {"symbol", "buy_price", "quantity"}
        for h in holdings:
            if not required_keys.issubset(h.keys()):
                print(f"Invalid holding entry: missing keys in {h.get('symbol', 'unknown')}")
                return None
        print(f"Portfolio imported: {len(holdings)} holdings from {filepath}")
        return holdings
    except Exception as e:
        print(f"Error importing portfolio from JSON: {e}")
        return None

def merge_portfolios(existing, imported):
    """
    Merges an imported portfolio into the existing one.
    - If a symbol exists in both, the imported values overwrite (update).
    - If a symbol is new, it's appended.
    Returns the merged list.
    """
    existing_syms = {h["symbol"] for h in existing}
    merged = list(existing)  # copy existing
    
    for h in imported:
        if h["symbol"] in existing_syms:
            # Update existing holding
            for i, eh in enumerate(merged):
                if eh["symbol"] == h["symbol"]:
                    merged[i].update(h)
                    break
        else:
            # Add new holding
            merged.append(h)
    
    return merged

def send_portfolio_via_email(holdings, recipient_email=None):
    """
    Sends the portfolio as a JSON attachment via email.
    Uses existing SMTP config.
    If recipient_email is provided, sends to that address.
    Otherwise falls back to EMAIL_RECIPIENTS env var.
    Returns (success: bool, message: str)
    """
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        import datetime
        
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASSWORD", "")
        recipients_str = os.getenv("EMAIL_RECIPIENTS", "")
        
        if not smtp_user or not smtp_pass:
            return False, "SMTP not configured (SMTP_USER / SMTP_PASSWORD missing)"
        
        # Determine recipients
        if recipient_email:
            recipients = [recipient_email.strip()]
        elif recipients_str:
            recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
        else:
            return False, "No recipient email provided and EMAIL_RECIPIENTS not set"
        
        # Export to JSON first
        json_path = export_portfolio_to_json(holdings)
        if not json_path:
            return False, "Failed to export portfolio to JSON"
        
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = f"📤 Bharat AI Portfolio Share - {datetime.date.today()}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>📤 Shared Portfolio</h2>
            <p>Please find attached my portfolio from <b>Bharat AI Fund Manager</b>.</p>
            <p><b>To import:</b> In the app, go to Portfolio → Import Portfolio and upload this file.</p>
            <p>Total holdings: <b>{len(holdings)}</b></p>
            <hr/>
            <p><i>Generated by Bharat AI Fund Manager Gill</i></p>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))
        
        with open(json_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename=portfolio_share.json")
            msg.attach(part)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipients, msg.as_string())
        
        print(f"Portfolio shared via email to {', '.join(recipients)}")
        return True, f"Portfolio shared with {len(recipients)} recipient(s)"
        
    except Exception as e:
        print(f"Error sharing portfolio via email: {e}")
        return False, str(e)
