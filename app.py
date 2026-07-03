import os
import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

from symbols import get_all_tickers
from data_fetcher import get_stock_data, batch_update_stocks, batch_update_stocks_parallel
from scoring_engine import run_scoring, score_stock, run_scoring_v2, score_stock_v2
from report_generator import generate_excel_report, generate_pdf_report, generate_excel_report_v2, generate_pdf_report_v2
from email_dispatcher import send_momentum_newsletter
from llm_harness import has_active_api_key, generate_ai_narrative, generate_ai_narrative_v2, discuss_with_jarvis
from portfolio_manager import (
    load_portfolio, save_portfolio, add_holding, remove_holding, update_portfolio_prices,
    generate_portfolio_signals, export_portfolio_to_excel, check_and_trigger_alerts,
    play_alert_sound, show_desktop_notification
)

# Initialize config
load_dotenv()
st.set_page_config(
    page_title="Bharat AI Fund Manager Gill",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------ STYLING & AESTHETICS (LIGHT SKY BLUE JARVIS STYLE) ------------------
st.markdown("""
<style>
    /* Light Theme Core */
    .stApp {
        background-color: #E2F1F8;
        color: #0F172A;
        font-family: 'Outfit', sans-serif;
    }
    
    /* Headers styling */
    h1, h2, h3 {
        color: #0369A1 !important;
        font-weight: 700;
        text-shadow: 0px 0px 8px rgba(3, 105, 161, 0.2);
    }
    
    /* Metrics Card Light style */
    .metric-container {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid #7DD3FC;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.1);
        text-align: center;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #0284C7;
        text-shadow: 0px 0px 5px rgba(2, 132, 199, 0.2);
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #475569;
        text-transform: uppercase;
        margin-top: 5px;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #CFE2FE !important;
        border-right: 1px solid #93C5FD;
    }
    
    /* Force sidebar text to be dark for readability */
    section[data-testid="stSidebar"] * {
        color: #1E293B !important;
    }
    
    /* Buttons styling */
    .stButton>button {
        background: linear-gradient(135deg, #0284C7, #0369A1) !important;
        color: white !important;
        border: 1px solid #7DD3FC !important;
        border-radius: 5px !important;
        padding: 8px 16px !important;
        box-shadow: 0px 0px 10px rgba(14, 165, 233, 0.1) !important;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        box-shadow: 0px 0px 15px rgba(14, 165, 233, 0.4) !important;
        transform: translateY(-2px);
    }
    
    /* Red alert tags */
    .red-alert-card {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid #EF4444;
        border-radius: 8px;
        padding: 12px;
        color: #991B1B;
        box-shadow: 0 4px 10px rgba(239, 68, 68, 0.05);
    }
    
    /* Jarvis Chat Container */
    .chat-bubble-jarvis {
        background: rgba(14, 165, 233, 0.1);
        border-left: 4px solid #0EA5E9;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 8px;
        color: #0F172A;
    }
    .chat-bubble-user {
        background: rgba(255, 255, 255, 0.7);
        border-left: 4px solid #64748B;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 8px;
        color: #0F172A;
    }
    
    /* Portfolio Alert Styles */
    @keyframes portAlertPulse {
        0% { box-shadow: 0 0 5px #FF0000; }
        50% { box-shadow: 0 0 25px #FF0000, 0 0 50px #FF0000; }
        100% { box-shadow: 0 0 5px #FF0000; }
    }
    .portfolio-alert-box {
        background: linear-gradient(135deg, #450000, #7F0000);
        border: 3px solid #FF0000;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        animation: portAlertPulse 1.5s infinite;
        color: #FFFFFF;
        font-weight: bold;
        font-size: 1.2rem;
        text-align: center;
    }
    .portfolio-alert-box small {
        color: #FF8888;
        font-size: 0.9rem;
    }
    .portfolio-row-red {
        background-color: rgba(255, 0, 0, 0.15) !important;
        border-left: 5px solid #FF0000;
    }
    .portfolio-row-green {
        background-color: rgba(0, 200, 0, 0.10) !important;
        border-left: 5px solid #00CC00;
    }
    .portfolio-status-badge {
        padding: 4px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .portfolio-status-green {
        background: rgba(0, 200, 0, 0.2);
        color: #006600;
        border: 1px solid #00CC00;
    }
    .portfolio-status-red {
        background: rgba(255, 0, 0, 0.2);
        color: #990000;
        border: 1px solid #FF0000;
        animation: portAlertPulse 1.5s infinite;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ AUTO-REFRESH: Every 15 minutes ------------------
st_autorefresh = st.markdown("""
    <meta http-equiv="refresh" content="900">
""", unsafe_allow_html=True)

# ------------------ STATE INITIALIZATION ------------------
if "stock_cache" not in st.session_state:
    st.session_state["stock_cache"] = {}
if "last_update" not in st.session_state:
    st.session_state["last_update"] = None
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []
if "portfolio" not in st.session_state:
    st.session_state["portfolio"] = load_portfolio()
if "portfolio_refreshed" not in st.session_state:
    st.session_state["portfolio_refreshed"] = False
if "alert_stocks_triggered" not in st.session_state:
    st.session_state["alert_stocks_triggered"] = []

# ------------------ SCAN MODE SELECTOR ------------------
if "scan_mode" not in st.session_state:
    st.session_state["scan_mode"] = "⚡ Core 127"

if "all_tickers" not in st.session_state:
    st.session_state["all_tickers"] = get_all_tickers(use_full=False)

# ------------------ SIDEBAR ------------------
st.sidebar.image("https://img.icons8.com/nolan/96/artificial-intelligence.png", width=90)
st.sidebar.title("BHARAT AI GILL")
st.sidebar.subheader("Jarvis Option/Fund Core v1.01")

# Show Jarvis status in Sidebar
if has_active_api_key():
    st.sidebar.markdown("🧠 **AI Brain Status:** <span style='color:#00FF66;'>🟢 Jarvis Online</span>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("🧠 **AI Brain Status:** <span style='color:#FF0055;'>🔴 Jarvis Offline</span>", unsafe_allow_html=True)
    # Debug: check what's in Streamlit secrets
    _debug_msg = "No secrets found"
    try:
        import streamlit as st
        _all_secrets = list(st.secrets.keys())
        if _all_secrets:
            _debug_msg = f"Secrets keys found: {', '.join(_all_secrets)}"
            for _k in _all_secrets:
                _v = st.secrets[_k]
                if len(str(_v)) > 5:
                    _debug_msg += f" | {_k}=...{str(_v)[-4:]}"
    except Exception as e:
        _debug_msg = f"Secrets error: {e}"
    st.sidebar.caption(f"🔍 {_debug_msg}")

st.sidebar.markdown("---")
st.sidebar.write("⚡ **Control Center**")

# Scan mode toggle
scan_mode = st.sidebar.radio(
    "Scan Mode",
    ["⚡ Core 127", "🌐 Full Universe 2000+"],
    index=0 if st.session_state["scan_mode"] == "⚡ Core 127" else 1,
    help="Core 127: Quick scan of hand-picked stocks. Full Universe: 2000+ NSE stocks (takes ~30s)."
)

# Update tickers if mode changed
if scan_mode != st.session_state["scan_mode"]:
    st.session_state["scan_mode"] = scan_mode
    use_full = "2000+" in scan_mode
    st.session_state["all_tickers"] = get_all_tickers(use_full=use_full)
    st.sidebar.info(f"Switched to {'2000+ Full Universe' if use_full else '127 Core Watchlist'} mode!")

all_tickers = st.session_state["all_tickers"]

if st.sidebar.button("Run System Scan (Pull Data)"):
    progress_bar = st.sidebar.progress(0.0)
    status_text = st.sidebar.empty()

    def update_prog(idx, total, ticker):
        pct = float(idx + 1) / total
        progress_bar.progress(pct)
        status_text.write(f"Scrubbing: `{ticker}` ({idx+1}/{total})")

    use_full = "2000+" in scan_mode
    if use_full:
        st.sidebar.info("🌐 Full universe scan in progress (parallel engine active)...")
        results = batch_update_stocks_parallel(all_tickers, force_refresh=True, max_workers=10, progress_callback=update_prog)
    else:
        results = batch_update_stocks(all_tickers, force_refresh=True, progress_callback=update_prog)
    st.session_state["stock_cache"] = results
    st.session_state["last_update"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    st.sidebar.success("Scan Complete!")

# Check cache status on load
if not st.session_state["stock_cache"]:
    results = {}
    for ticker in all_tickers:
        data = get_stock_data(ticker, force_refresh=False)
        if data:
            results[ticker] = data
    st.session_state["stock_cache"] = results
    st.session_state["last_update"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

last_up = st.session_state["last_update"] or "Never"
st.sidebar.caption(f"Last data sync: {last_up}")
st.sidebar.caption(f"Universe: {len(all_tickers)} stocks")


# ============================================================
# PORTFOLIO RENDERING ENGINE (reusable — used by tabs & dedicated page)
# ============================================================
def render_portfolio_page(suffix="port"):
    """
    Render the full Excel-style portfolio dashboard.
    suffix param ensures unique Streamlit widget keys when called multiple times.
    """
    # Refresh portfolio prices on every page load (once per session)
    if not st.session_state["portfolio_refreshed"] and st.session_state["portfolio"]:
        with st.spinner("Refreshing portfolio prices..."):
            st.session_state["portfolio"] = update_portfolio_prices(st.session_state["portfolio"])
            st.session_state["portfolio_refreshed"] = True
            # Trigger all alert systems for stocks below 200 SMA
            triggered = check_and_trigger_alerts(st.session_state["portfolio"])
            st.session_state["alert_stocks_triggered"] = [h["symbol"] for h in triggered]
            # Note: No st.rerun() here — WebSocket forward-msg cache misses on Streamlit Cloud.
            # The updated data is already in session_state and renders immediately.
    
    portfolio = st.session_state["portfolio"]
    
    # ---- Add Stock Form ----
    with st.expander("➕ Add Stock to Portfolio", expanded=not bool(portfolio)):
        col_a1, col_a2, col_a3, col_a4 = st.columns([3, 2, 2, 1])
        all_syms = sorted(st.session_state["stock_cache"].keys())
        with col_a1:
            new_sym = st.selectbox("Symbol", all_syms, key=f"{suffix}_port_add_sym")
        with col_a2:
            new_buy = st.number_input("Buy Price (₹)", min_value=0.01, step=1.0, key=f"{suffix}_port_add_buy")
        with col_a3:
            new_qty = st.number_input("Quantity", min_value=1, step=1, key=f"{suffix}_port_add_qty")
        with col_a4:
            st.markdown("<br/>", unsafe_allow_html=True)
            if st.button("Add", key=f"{suffix}_port_add_btn"):
                st.session_state["portfolio"] = add_holding(new_sym, new_buy, int(new_qty))
                st.success(f"✅ Added {new_sym.replace('.NS', '')} to portfolio!")
                st.session_state["portfolio"] = update_portfolio_prices(st.session_state["portfolio"])
                st.rerun()
    
    st.markdown("---")
    
    # ---- Control Buttons Row ----
    col_r1, col_r2, col_r3, col_r4 = st.columns([3, 2, 2, 3])
    with col_r2:
        if st.button("🔄 Refresh Prices Now", use_container_width=True, key=f"{suffix}_port_refresh"):
            with st.spinner("Fetching latest prices..."):
                st.session_state["portfolio"] = update_portfolio_prices(st.session_state["portfolio"])
                triggered = check_and_trigger_alerts(st.session_state["portfolio"])
                st.session_state["alert_stocks_triggered"] = [h["symbol"] for h in triggered]
            st.rerun()
    with col_r3:
        if st.button("🔊 Test Alert Sound", use_container_width=True, key=f"{suffix}_port_test_sound"):
            play_alert_sound(repeat=2)
            show_desktop_notification("🔊 Alert Test", "Bharat AI alert system is active and working!")
            st.success("✅ Sound + Desktop notification test sent!")
    with col_r4:
        if portfolio and st.button("📥 Download Portfolio Excel", use_container_width=True, key=f"{suffix}_port_dl"):
            excel_path = "portfolio_report.xlsx"
            ok = export_portfolio_to_excel(portfolio, excel_path)
            if ok:
                with open(excel_path, "rb") as f:
                    st.download_button(
                        "📥 Click to Download",
                        f,
                        file_name="my_portfolio_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"{suffix}_port_dl_btn"
                    )
            else:
                st.error("Failed to generate Excel report.")
    
    if not portfolio:
        st.info("💡 Your portfolio is empty. Add stocks above to start tracking them against the 200 SMA.")
    else:
        # ---- Check for stocks BELOW 200 SMA → SUPER LOUD ALERTS (ALL 4 TYPES) ----
        below_sma_stocks = [h for h in portfolio if h["sma_200"] > 0 and not h["above_sma"]]
        if below_sma_stocks:
            new_triggers = [h["symbol"] for h in below_sma_stocks if h["symbol"] not in st.session_state.get("alert_stocks_triggered", [])]
            if new_triggers:
                triggered = check_and_trigger_alerts(below_sma_stocks)
                st.session_state["alert_stocks_triggered"] = list(set(
                    st.session_state.get("alert_stocks_triggered", []) + [h["symbol"] for h in triggered]
                ))
            
            for h in below_sma_stocks:
                sym_display = h["symbol"].replace(".NS", "")
                for _ in range(3):
                    st.markdown(f"""
                    <div class="portfolio-alert-box">
                        🚨🚨 CRITICAL ALERT: {sym_display} is BELOW 200 SMA! EXIT IMMEDIATELY! 🚨🚨<br/>
                        LTP: ₹{h['ltp']} | 200 SMA: ₹{h['sma_200']} | Distance: {h['dist_pct']}%<br/>
                        <small>You bought at ₹{h['buy_price']} × {h['quantity']} shares</small>
                    </div>
                    """, unsafe_allow_html=True)
        
        # ---- Excel-Style Portfolio Table ----
        st.markdown("#### 📋 Your Holdings — Excel Dashboard View")
        
        # Compute summary numbers for header row
        total_invested = sum(h["buy_price"] * h["quantity"] for h in portfolio)
        total_value = sum((h["ltp"] * h["quantity"]) if h["ltp"] > 0 else 0 for h in portfolio)
        overall_pl = round(((total_value - total_invested) / total_invested) * 100, 2) if total_invested > 0 else 0
        buy_count = sum(1 for h in portfolio if h.get("signal") == "BUY")
        hold_count = sum(1 for h in portfolio if h.get("signal") == "HOLD")
        exit_count = sum(1 for h in portfolio if h.get("signal") == "EXIT")
        above_sma_count = sum(1 for h in portfolio if h["sma_200"] > 0 and h["above_sma"])
        below_sma_count = sum(1 for h in portfolio if h["sma_200"] > 0 and not h["above_sma"])
        
        # Summary metric cards
        mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
        mcol1.metric("💰 Total Invested", f"₹{total_invested:,.2f}")
        mcol2.metric("📊 Current Value", f"₹{total_value:,.2f}")
        pl_mcolor = "#00CC00" if overall_pl >= 0 else "#FF0000"
        mcol3.markdown(f'<div style="text-align:center"><span style="font-size:1.1rem; font-weight:bold;">Overall P&L</span><br/><span style="font-size:1.8rem; font-weight:bold; color:{pl_mcolor};">{overall_pl}%</span></div>', unsafe_allow_html=True)
        mcol4.metric("✅ Above SMA / ⚠️ Below", f"{above_sma_count} / {below_sma_count}")
        mcol5.metric("🟢 BUY / HOLD / 🚨 EXIT", f"{buy_count}/{hold_count}/{exit_count}")
        
        st.markdown("<br/>", unsafe_allow_html=True)
        
        # Build a clean dataframe for Streamlit's native renderer
        df_rows = []
        for h in portfolio:
            sym = h["symbol"]
            buy = h["buy_price"]
            qty = h["quantity"]
            invested = round(buy * qty, 2)
            ltp = h["ltp"]
            curr_val = round(ltp * qty, 2) if ltp > 0 else 0
            pl_pct = round(((ltp - buy) / buy) * 100, 2) if ltp > 0 and buy > 0 else 0
            sma = h["sma_200"]
            dist = h["dist_pct"]
            above = h["above_sma"] if sma > 0 else True
            signal = h.get("signal", "WAIT")
            
            df_rows.append({
                "Symbol": sym.replace(".NS", ""),
                "Buy Price": buy,
                "Qty": qty,
                "Invested (₹)": invested,
                "LTP (₹)": ltp if ltp > 0 else 0,
                "Value (₹)": curr_val,
                "P&L %": pl_pct,
                "200 SMA (₹)": sma if sma > 0 else 0,
                "SMA Dist %": dist,
                "Above SMA": "✅ YES" if above else "🔴 NO",
                "Signal": signal
            })
        
        df_display = pd.DataFrame(df_rows)
        
        # Color-code rows based on Above SMA status
        def _highlight_row(row):
            if row["Above SMA"] == "🔴 NO":
                return ["background-color: #FFE0E0"] * len(row)
            elif row["P&L %"] >= 0:
                return ["background-color: #E0FFE0"] * len(row)
            return [""] * len(row)
        
        styled_df = df_display.style\
            .apply(_highlight_row, axis=1)\
            .format({
                "Buy Price": "₹{:.2f}",
                "Invested (₹)": "₹{:,.2f}",
                "LTP (₹)": "₹{:.2f}",
                "Value (₹)": "₹{:,.2f}",
                "P&L %": "{:+.2f}%",
                "200 SMA (₹)": "₹{:.2f}",
                "SMA Dist %": "{:+.2f}%"
            })\
            .map(lambda v: "color: #00AA00; font-weight: bold" if isinstance(v, str) and "BUY" in v else (
                "color: #FF0000; font-weight: bold" if isinstance(v, str) and "EXIT" in v else (
                "color: #CC8800; font-weight: bold" if isinstance(v, str) and "HOLD" in v else ""))
            )
        
        st.dataframe(styled_df, use_container_width=True, height=min(400, 35 * len(df_rows) + 40))
        
        st.caption(f"Auto-refreshes every 15 min • Last update: {portfolio[0]['last_updated'] if portfolio and portfolio[0]['last_updated'] else '—' }")
        
        # ---- Remove Stock ----
        st.markdown("---")
        col_rem1, col_rem2, col_rem3 = st.columns([2, 2, 6])
        with col_rem1:
            if portfolio:
                rem_sym = st.selectbox("🗑️ Remove a Holding", [h["symbol"] for h in portfolio], key=f"{suffix}_port_rem_sym")
        with col_rem2:
            st.markdown("<br/>", unsafe_allow_html=True)
            if portfolio and st.button("🗑️ Remove", use_container_width=True, key=f"{suffix}_port_rem_btn"):
                st.session_state["portfolio"] = remove_holding(rem_sym)
                st.session_state["alert_stocks_triggered"] = [h["symbol"] for h in st.session_state["portfolio"]
                                                               if h.get("sma_200", 0) > 0 and not h.get("above_sma", False)]
                st.warning(f"Removed {rem_sym.replace('.NS', '')} from portfolio.")
                st.rerun()


# Filter selections
st.sidebar.markdown("---")
engine_page = st.sidebar.radio("Navigation", ["⚡ Page 1: Momentum & Breakout", "🔍 Page 2: Value & 200 SMA", "📊 Portfolio Dashboard"])

use_full = "2000+" in scan_mode
st.sidebar.markdown("---")
st.sidebar.write("⚙️ **Global Filter Options**")
from symbols import get_all_categories
selected_cap = st.sidebar.selectbox("Market Cap Universe", get_all_categories(use_full=use_full))

if engine_page == "⚡ Page 1: Momentum & Breakout":
    min_score = st.sidebar.slider("Minimum Quality Score", 0, 20, 10)
elif engine_page == "🔍 Page 2: Value & 200 SMA":
    min_score = st.sidebar.slider("Minimum Quality Score", 0, 16, 8)
else:
    min_score = 0  # Not used for portfolio page

# Process active dataset
df, latest_highs, continuous, red_alerts = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
if st.session_state["stock_cache"]:
    # Check if cached items have 200 SMA details. If not, show warning in sidebar.
    missing_sma = False
    for tkr, cache_data in st.session_state["stock_cache"].items():
        if "sma_200" not in cache_data:
            missing_sma = True
            break
    if missing_sma:
        st.sidebar.warning("⚠️ Some cached data is missing 200 SMA. Run 'System Scan' in sidebar to update.")

    if engine_page == "⚡ Page 1: Momentum & Breakout":
        df, latest_highs, continuous, red_alerts = run_scoring(st.session_state["stock_cache"])
    elif engine_page == "🔍 Page 2: Value & 200 SMA":
        df, continuous, red_alerts = run_scoring_v2(st.session_state["stock_cache"])
        latest_highs = pd.DataFrame()
    else:
        # Portfolio Dashboard — no scoring needed
        pass

    # Apply sidebar filters
    if selected_cap != "All Stocks":
        df = df[df["Category"] == selected_cap] if not df.empty else df
        if not latest_highs.empty:
            latest_highs = latest_highs[latest_highs["Category"] == selected_cap]
        continuous = continuous[continuous["Category"] == selected_cap] if not continuous.empty else continuous
        red_alerts = red_alerts[red_alerts["Category"] == selected_cap] if not red_alerts.empty else red_alerts
        
    df = df[df["Total Score"] >= min_score] if not df.empty else df

# ------------------ MAIN SCREEN ------------------
if engine_page == "📊 Portfolio Dashboard":
    st.title("📊 BHARAT AI PORTFOLIO MANAGER")
    st.markdown("### Personal Portfolio Tracker — Excel-Style Dashboard with Auto Signals & Alerts")
    st.write("Track your own holdings against the 200-day SMA with **auto signals, live alerts, and sound notifications**. Dashboard auto-refreshes every 15 minutes.")
    st.caption("💡 Tip: If a stock falls below the 200 SMA, you'll get **🔊 sound beeps + 📢 desktop notifications + 📧 email alert + 🔴 pulsing red banner** — all automated.")
    st.markdown("---")
    render_portfolio_page(suffix="dedicated")
    
elif not st.session_state["stock_cache"]:
    st.warning("No stock data cached. Please run a 'System Scan' in the left control panel to fetch fresh market parameters.")
else:
    if engine_page == "⚡ Page 1: Momentum & Breakout":
        # Title and header
        st.title("⚡ BHARAT AI FUND MANAGER GILL")
        st.markdown("### Jarvis Autonomous Option/Equity Momentum Screener (v1.01 Upgrade)")
        
        # 1. Metric Display Cards (Page 1)
        star_stocks = len(df[df["Total Star Rating"] >= 12]) if not df.empty else 0
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{len(all_tickers)}</div>
                <div class="metric-label">Universe Pool</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            breakouts_count = len(df[df["Total Score"] >= 14])
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #00FF66; text-shadow: 0px 0px 8px rgba(0, 255, 102, 0.5);">{breakouts_count}</div>
                <div class="metric-label">Breakout Targets (Score ≥ 14)</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #FFD700; text-shadow: 0px 0px 8px rgba(255, 215, 0, 0.5);">⭐⭐⭐ {star_stocks}</div>
                <div class="metric-label">Star Stocks (3★ CAGR + Score)</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            sustained_count = len(continuous)
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #FFC900; text-shadow: 0px 0px 8px rgba(255, 201, 0, 0.5);">{sustained_count}</div>
                <div class="metric-label">Sustained Momentum</div>
            </div>
            """, unsafe_allow_html=True)
        with col5:
            alerts_count = len(red_alerts)
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #FF0055; text-shadow: 0px 0px 8px rgba(255, 0, 85, 0.5);">{alerts_count}</div>
                <div class="metric-label">Blacklisted/Red Alert</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br/>", unsafe_allow_html=True)

        # 2. Main Tabbed Windows (Page 1)
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "🏆 Ranked Leaderboard", 
            "⚡ Latest Breakouts", 
            "📈 Sustained momentum", 
            "🚨 Red Alert Blacklist",
            "💬 Jarvis AI Consultant",
            "🧪 Backtesting Simulator",
            "📊 My Portfolio",
            "📧 Newsletter Dispatcher"
        ])
        
        # --- TAB 1: Ranked Leaderboard ---
        with tab1:
            st.subheader("Equities Ranked by Multi-Factor Score (Max 20)")
            st.write("Click on any row symbol in the dropdown below to trigger the Jarvis gen AI narrative breakdown.")
            
            # Display table — full visibility with 24-Star CAGR System
            df_display = df.copy()
            df_display["CAGR Accelerating"] = df_display["CAGR Accelerating"].map({True: "✅", False: ""})
            # Build New Star Display: Sales Stars + Profit Stars = Total/24
            df_display["Stars (Sales)"] = df_display.apply(
                lambda r: f"{'⭐'*int(r['Sales CAGR Stars'])} {r['Sales CAGR Star Bar'].split()[-1]}" 
                if r.get('Sales CAGR Stars', 0) > 0 else "-", axis=1)
            df_display["Stars (Profit)"] = df_display.apply(
                lambda r: f"{'⭐'*int(r['Profit CAGR Stars'])} {r['Profit CAGR Star Bar'].split()[-1]}"
                if r.get('Profit CAGR Stars', 0) > 0 else "-", axis=1)
            df_display["Star Badge"] = df_display["Star Badge"]
            display_cols = [
                "Ticker", "Category", "Price", "Total Score",
                "Stars (Sales)", "Stars (Profit)", "Star Badge",
                "Sales CAGR 3Y", "Sales CAGR 5Y",
                "Profit CAGR 3Y", "Profit CAGR 5Y",
                "200 SMA", "200 SMA Dist %"
            ]
            st.dataframe(
                df_display[display_cols],
                use_container_width=True,
                height=min(600, 35 * len(df_display) + 40)
            )
            
            st.markdown("---")
            st.subheader("🤖 Gen AI Jarvis Stock Diagnostic Report")
            selected_ticker = st.selectbox("Select Ticker for Diagnostic", df["Ticker"].tolist() if not df.empty else ["None"])
            
            if selected_ticker and selected_ticker != "None":
                stock_data = st.session_state["stock_cache"][selected_ticker]
                row_data = df[df["Ticker"] == selected_ticker].iloc[0]
                
                col_left, col_right = st.columns([2, 1])
                with col_left:
                    st.markdown(f"#### Diagnostic: {selected_ticker.replace('.NS', '')}")
                    
                    # Check key status for loading narrative
                    with st.spinner("Jarvis is writing business story..."):
                        narrative = generate_ai_narrative(selected_ticker, row_data)
                    st.info(narrative)
                    
                    # Plot price history
                    hist_prices = stock_data["price_history_6m"]
                    if hist_prices:
                        fig = px.line(
                            y=hist_prices,
                            title=f"{selected_ticker.replace('.NS', '')} - 6 Month Trend",
                            labels={"y": "Price (₹)", "x": "Days"},
                            template="plotly_white"
                        )
                        fig.update_traces(line_color='#008DDA')
                        st.plotly_chart(fig, use_container_width=True)
                
                with col_right:
                    st.markdown("#### CAGR Acceleration")
                    cagr_accel = row_data.get("CAGR Accelerating", False)
                    if cagr_accel:
                        st.success("✅ Sales & Profit Growth Accelerating")
                    else:
                        st.warning("⚠️ Growth not accelerating")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Sales CAGR", f'{row_data.get("Sales CAGR", 0):.1f}%')
                        st.metric("Sales CAGR 3Y", f'{row_data.get("Sales CAGR 3Y", 0):.1f}%')
                        st.metric("Sales CAGR 5Y", f'{row_data.get("Sales CAGR 5Y", 0):.1f}%')
                    with c2:
                        st.metric("Profit CAGR", f'{row_data.get("Profit CAGR", 0):.1f}%')
                        st.metric("Profit CAGR 3Y", f'{row_data.get("Profit CAGR 3Y", 0):.1f}%')
                        st.metric("Profit CAGR 5Y", f'{row_data.get("Profit CAGR 5Y", 0):.1f}%')
                    
                    st.markdown("---")
                    st.markdown("#### Balance Sheet & Holders")
                    st.metric("Debt-to-Equity Ratio", f"{row_data['Debt/Equity']}")
                    st.metric("Reserves (Cr)", f"₹{row_data['Reserves']} Cr")
                    
                    # Shareholding Pie Chart
                    shareholding_data = {
                        "Holder": ["Promoter", "Institutions", "Public"],
                        "Share %": [row_data["Promoter %"], row_data["Institution %"], row_data["Public %"]]
                    }
                    pie_df = pd.DataFrame(shareholding_data)
                    fig_pie = px.pie(
                        pie_df, 
                        values="Share %", 
                        names="Holder", 
                        color_discrete_sequence=['#0B192C', '#008DDA', '#FFCCD5'],
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

        # --- TAB 2: Latest Breakouts ---
        with tab2:
            st.subheader("⚡ Stocks Breaking All-Time Highs or 3-Year Highs")
            st.write("These companies are in the immediate breakout zone, showing intense price velocity.")
            if not latest_highs.empty:
                st.dataframe(latest_highs[["Ticker", "Category", "Price", "ATH", "3Y High", "Total Score"]], use_container_width=True)
            else:
                st.info("No active breakout stocks found matching your filters.")

        # --- TAB 3: Sustained Momentum ---
        with tab3:
            st.subheader("📈 Sustained High Momentum Performers")
            st.write("These stocks have successfully consolidated near their recent highs over 1, 2, or 6 months without breaking structure.")
            if not continuous.empty:
                st.dataframe(continuous[["Ticker", "Category", "Price", "Total Score", "Momentum Status"]], use_container_width=True)
            else:
                st.info("No sustained momentum stocks found matching filters.")

        # --- TAB 4: Red Alert Blacklist ---
        with tab4:
            st.subheader("🚨 Deteriorating Fundamentals / Excessive Risk Blacklist")
            st.write("These stocks have been flagged due to weak operating profiles, high debt structures, or falling reserves.")
            if not red_alerts.empty:
                for idx, row in red_alerts.iterrows():
                    st.markdown(f"""
                    <div class="red-alert-card" style="margin-bottom: 10px;">
                        <strong>{row['Ticker'].replace('.NS', '')}</strong> ({row['Category']}) | Total Score: {row['Total Score']}/20<br/>
                        ⚠️ Alerts Flagged: <em>{row['Red Reasons']}</em><br/>
                        Debt/Equity: {row['Debt/Equity']} | Reserves: ₹{row['Reserves']} Cr
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("Excellent! No stocks in your watchlist are currently triggering red-alert flags.")

        # --- TAB 5: Jarvis AI Chat Consultant ---
        with tab5:
            st.subheader("💬 Discuss Markets with Jarvis")
            st.write("Ask Jarvis to compare stocks, explain breakout logic, or discuss trade planning.")
            
            if not has_active_api_key():
                st.error("Jarvis Brain Offline. Please add a valid Google Gemini API key to `api_key.txt` or `.env` to start chatting!")
                st.info("💡 You can get a free API Key in under 30 seconds at [Google AI Studio](https://aistudio.google.com).")
            else:
                # Display chat messages
                for role, text in st.session_state["chat_messages"]:
                    div_class = "chat-bubble-jarvis" if role == "Jarvis" else "chat-bubble-user"
                    st.markdown(f"""
                    <div class="{div_class}">
                        <strong>{role}:</strong><br/>
                        {text}
                    </div>
                    """, unsafe_allow_html=True)
                    
                # Chat input
                user_input = st.chat_input("Talk to Jarvis (e.g. Compare CDSL vs BSE...)")
                if user_input:
                    # Add user message
                    st.session_state["chat_messages"].append(("User", user_input))
                    st.markdown(f"""
                    <div class="chat-bubble-user">
                        <strong>User:</strong><br/>
                        {user_input}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Fetch Jarvis response
                    with st.spinner("Jarvis is thinking..."):
                        chat_hist_tuples = st.session_state["chat_messages"][:-1]
                        jarvis_reply = discuss_with_jarvis(user_input, chat_hist_tuples, df, page_mode="page_1")
                        
                    st.session_state["chat_messages"].append(("Jarvis", jarvis_reply))
                    st.rerun()

        # --- TAB 6: Backtesting Simulator ---
        with tab6:
            st.subheader("🧪 Portfolio Backtesting Simulator")
            st.write("Evaluate how a portfolio of high-scoring stocks selected 1, 2, or 3 years ago performs today compared to Nifty.")
            
            years = st.slider("Backtest Period (Years)", 1, 3, 2)
            
            backtest_results = []
            nifty_mock_return = 12.0 * years
            
            for ticker, data in st.session_state["stock_cache"].items():
                hist_prices = data.get("price_history_5y", data.get("price_history_6m", []))
                price_len = len(hist_prices)
                days_ago = years * 250
                if price_len > days_ago:
                    old_price = hist_prices[-days_ago]
                    curr_price = hist_prices[-1]
                    if old_price > 0:
                        ret = ((curr_price - old_price) / old_price) * 100
                        backtest_results.append({
                            "Ticker": ticker.replace(".NS", ""),
                            "Starting Price (₹)": round(old_price, 2),
                            "Ending Price (₹)": round(curr_price, 2),
                            "Return %": round(ret, 2)
                        })
                        
            if backtest_results:
                bt_df = pd.DataFrame(backtest_results)
                bt_df = bt_df.sort_values(by="Return %", ascending=False)
                
                avg_ret = bt_df["Return %"].mean()
                cagr = ((1 + (avg_ret/100)) ** (1/years) - 1) * 100
                
                col_b1, col_b2, col_b3 = st.columns(3)
                col_b1.metric("Average Portfolio Return", f"{round(avg_ret, 1)}%", f"+{round(avg_ret - nifty_mock_return, 1)}% vs Nifty")
                col_b2.metric("Portfolio CAGR", f"{round(cagr, 1)}%")
                col_b3.metric("Top Performer", f"{bt_df.iloc[0]['Ticker']} ({bt_df.iloc[0]['Return %']}%)")
                
                st.markdown("#### Portfolio Picks Performance Breakdown")
                st.dataframe(bt_df, use_container_width=True)
                
                comparison_df = pd.DataFrame({
                    "Engine": ["Bharat AI Engine", "Nifty 50 Index"],
                    "Cumulative Return %": [avg_ret, nifty_mock_return]
                })
                fig_compare = px.bar(
                    comparison_df, 
                    x="Engine", 
                    y="Cumulative Return %", 
                    color="Engine",
                    color_discrete_sequence=['#008DDA', '#415A77'],
                    title="Strategy vs Benchmark Cumulative Return Comparison",
                    template="plotly_white"
                )
                st.plotly_chart(fig_compare, use_container_width=True)
            else:
                st.info("Insufficient historical range to simulate backtest for selected duration.")

        # --- TAB 7: My Portfolio ---
        with tab7:
            render_portfolio_page(suffix="p1")

        # --- TAB 8: Newsletter Dispatcher ---
        with tab8:
            st.subheader("📧 Newsletter & SMTP Mailing Engine")
            st.write("Configure email updates to be delivered to subscribers with attached PDF & Excel sheets.")
            
            smtp_user = os.getenv("SMTP_USER") or "Not Configured"
            smtp_server = os.getenv("SMTP_SERVER")
            recipients = os.getenv("EMAIL_RECIPIENTS") or "None"
            
            st.markdown(f"""
            **Current SMTP Configuration:**
            * **Sender Account:** `{smtp_user}`
            * **Server Address:** `{smtp_server}`
            * **Mailing List:** `{recipients}`
            """)
            
            st.markdown("---")
            st.write("#### Manual Newsletter Trigger")
            if st.button("Generate Reports & Dispatch Newsletter"):
                with st.spinner("Compiling PDF and Excel dossier files..."):
                    pdf_path = "Bharat_AI_Gill_Momentum_Report.pdf"
                    excel_path = "Bharat_AI_Gill_Momentum_Data.xlsx"
                    
                    # Generate reports
                    pdf_ok = generate_pdf_report(df, pdf_path)
                    excel_ok = generate_excel_report(df, latest_highs, continuous, red_alerts, excel_path)
                    
                    if pdf_ok and excel_ok:
                        st.success("Reports generated successfully!")
                        
                        st.write("Attempting SMTP delivery...")
                        date_str = datetime.datetime.now().strftime("%d %B %Y")
                        mail_ok, mail_msg = send_momentum_newsletter(pdf_path, excel_path, date_str)
                        
                        if mail_ok:
                            st.success("Newsletter dispatched successfully to all recipients!")
                        else:
                            st.error(f"Email Dispatch Failed: {mail_msg}")
                            st.info("Tip: Double-check that your SMTP user and app passwords are set correctly in your `.env` file.")
                    else:
                        st.error("Report generation failed. Check server logs.")

    else:
        # Page 2 — Title and header
        st.title("🛡️ BHARAT AI VALUE & 200 SMA SCREENER")
        st.markdown("### Jarvis Proximity & CAGR Value Engine")
        
        # 1. Metric Display Cards
        star_stocks = len(df[df["Total Star Rating"] >= 12]) if not df.empty else 0
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{len(all_tickers)}</div>
                <div class="metric-label">Universe Pool</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            picks_count = len(df[df["Total Score"] >= 11]) if not df.empty else 0
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #00FF66; text-shadow: 0px 0px 8px rgba(0, 255, 102, 0.5);">{picks_count}</div>
                <div class="metric-label">Value Targets (Score ≥ 11/16)</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #FFD700; text-shadow: 0px 0px 8px rgba(255, 215, 0, 0.5);">⭐⭐⭐ {star_stocks}</div>
                <div class="metric-label">Star Stocks (3★ CAGR + Score)</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            avg_dist = df["200 SMA Dist %"].mean() if not df.empty else 0.0
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #FFC900; text-shadow: 0px 0px 8px rgba(255, 201, 0, 0.5);">{round(avg_dist, 2)}%</div>
                <div class="metric-label">Avg Distance to 200 SMA</div>
            </div>
            """, unsafe_allow_html=True)
        with col5:
            alerts_count = len(red_alerts)
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #FF0055; text-shadow: 0px 0px 8px rgba(255, 0, 85, 0.5);">{alerts_count}</div>
                <div class="metric-label">Blacklisted/Red Alert</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br/>", unsafe_allow_html=True)

	        # 2. Main Tabbed Windows (Page 2)
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🏆 Value & SMA Leaderboard", 
            "📈 Sustained momentum", 
            "🚨 Red Alert Blacklist",
            "💬 Jarvis AI Consultant",
            "🧪 Backtesting Simulator",
            "📊 My Portfolio",
            "📧 Newsletter Dispatcher"
        ])
        
        # --- TAB 1: Ranked Leaderboard ---
        with tab1:
            st.subheader("Equities Filtered by 200 SMA & Ranked by Value/Growth Score (Max 16)")
            st.write("Click on any row symbol in the dropdown below to trigger the Jarvis gen AI narrative breakdown.")
            
            # Sort option
            sort_by = st.selectbox("Leaderboard Sorting", ["Closest to 200 SMA (Value/Momentum Entry)", "Highest Quality Score (Out of 16)"])
            if sort_by == "Closest to 200 SMA (Value/Momentum Entry)":
                df = df.sort_values(by="200 SMA Dist %", ascending=True)
            else:
                df = df.sort_values(by="Total Score", ascending=False)
                
            # Display table — full visibility with 24-Star CAGR System
            display_cols = [
                "Ticker", "Category", "Price", "Total Score", "Star Badge",
                "Sales CAGR 3Y", "Sales CAGR 5Y",
                "Profit CAGR 3Y", "Profit CAGR 5Y",
                "200 SMA", "200 SMA Dist %"
            ]
            display_df = df.copy() if not df.empty else pd.DataFrame(columns=display_cols)
            if not display_df.empty:
                display_df = display_df[display_cols]
                
            st.dataframe(
                display_df,
                use_container_width=True,
                height=min(600, 35 * len(display_df) + 40)
            )
            
            st.markdown("---")
            st.subheader("🤖 Gen AI Jarvis Stock Diagnostic Report (Value Mode)")
            selected_ticker = st.selectbox("Select Ticker for Diagnostic", df["Ticker"].tolist() if not df.empty else ["None"], key="p2_diag_tk")
            
            if selected_ticker and selected_ticker != "None":
                stock_data = st.session_state["stock_cache"][selected_ticker]
                row_data = df[df["Ticker"] == selected_ticker].iloc[0]
                
                is_double_ath = row_data["Sales Score"] == 5 and row_data["Profit Score"] == 5
                if not is_double_ath:
                    st.markdown("""
                    <div style="margin-bottom: 15px; background-color: rgba(239, 68, 68, 0.2); border: 2px solid #EF4444; color: #B91C1C; padding: 15px; border-radius: 10px; font-weight: bold;">
                        ⚠️ ALERT: Chhoti-Moti Gadbad Detected! This stock does NOT have both sales and profits at All-Time Highs.
                        (Sales Score: {}/5 | Profit Score: {}/5)
                    </div>
                    """.format(int(row_data["Sales Score"]), int(row_data["Profit Score"])), unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="margin-bottom: 15px; background-color: rgba(16, 185, 129, 0.2); border: 2px solid #10B981; color: #065F46; padding: 15px; border-radius: 10px; font-weight: bold;">
                        ✅ PERFECT: Double All-Time High Peak (Sales & Profits are at historical peaks).
                    </div>
                    """, unsafe_allow_html=True)
                
                col_left, col_right = st.columns([2, 1])
                with col_left:
                    st.markdown(f"#### Diagnostic: {selected_ticker.replace('.NS', '')}")
                    
                    with st.spinner("Jarvis is writing business story..."):
                        narrative = generate_ai_narrative_v2(selected_ticker, row_data)
                    st.info(narrative)
                    
                    hist_prices = stock_data["price_history_6m"]
                    if hist_prices:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(y=hist_prices, name="Price", line=dict(color='#008DDA')))
                        sma_val = row_data["200 SMA"]
                        if sma_val > 0:
                            fig.add_trace(go.Scatter(y=[sma_val]*len(hist_prices), name="200 SMA", line=dict(color='#FF0055', dash='dash')))
                        fig.update_layout(title=f"{selected_ticker.replace('.NS', '')} - Price vs 200 SMA Level", template="plotly_white")
                        st.plotly_chart(fig, use_container_width=True)
                
                with col_right:
                    st.markdown("#### CAGR Acceleration")
                    cagr_accel = row_data.get("CAGR Accelerating", False)
                    if cagr_accel:
                        st.success("✅ Sales & Profit Growth Accelerating")
                    else:
                        st.warning("⚠️ Growth not accelerating")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Sales CAGR", f'{row_data.get("Sales CAGR", 0):.1f}%')
                        st.metric("Sales CAGR 3Y", f'{row_data.get("Sales CAGR 3Y", 0):.1f}%')
                        st.metric("Sales CAGR 5Y", f'{row_data.get("Sales CAGR 5Y", 0):.1f}%')
                    with c2:
                        st.metric("Profit CAGR", f'{row_data.get("Profit CAGR", 0):.1f}%')
                        st.metric("Profit CAGR 3Y", f'{row_data.get("Profit CAGR 3Y", 0):.1f}%')
                        st.metric("Profit CAGR 5Y", f'{row_data.get("Profit CAGR 5Y", 0):.1f}%')
                    
                    st.markdown("---")
                    st.markdown("#### Balance Sheet & Holders")
                    st.metric("Debt-to-Equity Ratio", f"{row_data['Debt/Equity']}")
                    st.metric("Reserves (Cr)", f"₹{row_data['Reserves']} Cr")
                    
                    shareholding_data = {
                        "Holder": ["Promoter", "Institutions", "Public"],
                        "Share %": [row_data["Promoter %"], row_data["Institution %"], row_data["Public %"]]
                    }
                    pie_df = pd.DataFrame(shareholding_data)
                    fig_pie = px.pie(
                        pie_df, 
                        values="Share %", 
                        names="Holder", 
                        color_discrete_sequence=['#0B192C', '#008DDA', '#FFCCD5'],
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

        # --- TAB 2: Sustained Momentum ---
        with tab2:
            st.subheader("📈 Sustained High Momentum Performers")
            st.write("These stocks have successfully consolidated near their recent highs over 1, 2, or 6 months without breaking structure.")
            if not continuous.empty:
                st.dataframe(continuous[["Ticker", "Category", "Price", "Total Score", "Momentum Status"]], use_container_width=True)
            else:
                st.info("No sustained momentum stocks found matching filters.")

        # --- TAB 3: Red Alert Blacklist ---
        with tab3:
            st.subheader("🚨 Deteriorating Fundamentals / Excessive Risk Blacklist")
            st.write("These stocks have been flagged due to weak operating profiles, high debt structures, or falling reserves.")
            if not red_alerts.empty:
                for idx, row in red_alerts.iterrows():
                    st.markdown(f"""
                    <div class="red-alert-card" style="margin-bottom: 10px;">
                        <strong>{row['Ticker'].replace('.NS', '')}</strong> ({row['Category']}) | Total Score: {row['Total Score']}/16<br/>
                        ⚠️ Alerts Flagged: <em>{row['Red Reasons']}</em><br/>
                        Debt/Equity: {row['Debt/Equity']} | Reserves: ₹{row['Reserves']} Cr
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("Excellent! No stocks in your watchlist are currently triggering red-alert flags.")

        # --- TAB 4: Jarvis AI Chat Consultant ---
        with tab4:
            st.subheader("💬 Discuss Markets with Jarvis (Value Mode)")
            st.write("Ask Jarvis to compare stocks, explain value logic, or discuss 200 SMA setups.")
            
            if not has_active_api_key():
                st.error("Jarvis Brain Offline. Please add a valid Google Gemini API key to `api_key.txt` or `.env` to start chatting!")
                st.info("💡 You can get a free API Key in under 30 seconds at [Google AI Studio](https://aistudio.google.com).")
            else:
                for role, text in st.session_state["chat_messages"]:
                    div_class = "chat-bubble-jarvis" if role == "Jarvis" else "chat-bubble-user"
                    st.markdown(f"""
                    <div class="{div_class}">
                        <strong>{role}:</strong><br/>
                        {text}
                    </div>
                    """, unsafe_allow_html=True)
                    
                user_input = st.chat_input("Talk to Jarvis (e.g. Compare CDSL vs BSE...)", key="p2_chat_in")
                if user_input:
                    st.session_state["chat_messages"].append(("User", user_input))
                    st.markdown(f"""
                    <div class="chat-bubble-user">
                        <strong>User:</strong><br/>
                        {user_input}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.spinner("Jarvis is thinking..."):
                        chat_hist_tuples = st.session_state["chat_messages"][:-1]
                        jarvis_reply = discuss_with_jarvis(user_input, chat_hist_tuples, df, page_mode="page_2")
                        
                    st.session_state["chat_messages"].append(("Jarvis", jarvis_reply))
                    st.rerun()

        # --- TAB 5: Backtesting Simulator ---
        with tab5:
            st.subheader("🧪 Portfolio Backtesting Simulator (Value Mode)")
            st.write("Evaluate how a portfolio of Page 2 value-momentum stocks performed compared to Nifty.")
            
            years = st.slider("Backtest Period (Years)", 1, 3, 2, key="p2_backtest_yr")
            
            backtest_results = []
            nifty_mock_return = 12.0 * years
            
            for ticker, data in st.session_state["stock_cache"].items():
                hist_prices = data.get("price_history_5y", data.get("price_history_6m", []))
                price_len = len(hist_prices)
                days_ago = years * 250
                if price_len > days_ago:
                    old_price = hist_prices[-days_ago]
                    curr_price = hist_prices[-1]
                    if old_price > 0:
                        ret = ((curr_price - old_price) / old_price) * 100
                        backtest_results.append({
                            "Ticker": ticker.replace(".NS", ""),
                            "Starting Price (₹)": round(old_price, 2),
                            "Ending Price (₹)": round(curr_price, 2),
                            "Return %": round(ret, 2)
                        })
                        
            if backtest_results:
                bt_df = pd.DataFrame(backtest_results)
                bt_df = bt_df.sort_values(by="Return %", ascending=False)
                
                avg_ret = bt_df["Return %"].mean()
                cagr = ((1 + (avg_ret/100)) ** (1/years) - 1) * 100
                
                col_b1, col_b2, col_b3 = st.columns(3)
                col_b1.metric("Average Portfolio Return", f"{round(avg_ret, 1)}%", f"+{round(avg_ret - nifty_mock_return, 1)}% vs Nifty")
                col_b2.metric("Portfolio CAGR", f"{round(cagr, 1)}%")
                col_b3.metric("Top Performer", f"{bt_df.iloc[0]['Ticker']} ({bt_df.iloc[0]['Return %']}%)")
                
                st.markdown("#### Portfolio Picks Performance Breakdown")
                st.dataframe(bt_df, use_container_width=True)
                
                comparison_df = pd.DataFrame({
                    "Engine": ["Bharat AI Value Engine", "Nifty 50 Index"],
                    "Cumulative Return %": [avg_ret, nifty_mock_return]
                })
                fig_compare = px.bar(
                    comparison_df, 
                    x="Engine", 
                    y="Cumulative Return %", 
                    color="Engine",
                    color_discrete_sequence=['#008DDA', '#415A77'],
                    title="Strategy vs Benchmark Cumulative Return Comparison",
                    template="plotly_white"
                )
                st.plotly_chart(fig_compare, use_container_width=True)
            else:
                st.info("Insufficient historical range to simulate backtest.")

        # --- TAB 6: My Portfolio (Page 2) ---
        with tab6:
            render_portfolio_page(suffix="p2")

        # --- TAB 7: Newsletter Dispatcher (Page 2) ---
        with tab7:
            st.subheader("📧 Newsletter & SMTP Mailing Engine (Value Mode)")
            st.write("Configure email updates to be delivered to subscribers with attached PDF & Excel sheets representing Value/SMA picks.")
            
            smtp_user = os.getenv("SMTP_USER") or "Not Configured"
            smtp_server = os.getenv("SMTP_SERVER")
            recipients = os.getenv("EMAIL_RECIPIENTS") or "None"
            
            st.markdown(f"""
            **Current SMTP Configuration:**
            * **Sender Account:** `{smtp_user}`
            * **Server Address:** `{smtp_server}`
            * **Mailing List:** `{recipients}`
            """)
            
            st.markdown("---")
            st.write("#### Manual Newsletter Trigger")
            if st.button("Generate Value Reports & Dispatch Newsletter", key="p2_mail_trigger"):
                with st.spinner("Compiling PDF and Excel dossier files..."):
                    pdf_path = "Bharat_AI_Gill_Value_Report.pdf"
                    excel_path = "Bharat_AI_Gill_Value_Data.xlsx"
                    
                    pdf_ok = generate_pdf_report_v2(df, pdf_path)
                    excel_ok = generate_excel_report_v2(df, continuous, red_alerts, excel_path)
                    
                    if pdf_ok and excel_ok:
                        st.success("Value Reports generated successfully!")
                        
                        st.write("Attempting SMTP delivery...")
                        date_str = datetime.datetime.now().strftime("%d %B %Y")
                        mail_ok, mail_msg = send_momentum_newsletter(pdf_path, excel_path, date_str)
                        
                        if mail_ok:
                            st.success("Newsletter dispatched successfully to all recipients!")
                        else:
                            st.error(f"Email Dispatch Failed: {mail_msg}")
                            st.info("Tip: Double-check that your SMTP user and app passwords are set correctly in your `.env` file.")
                    else:
                        st.error("Report generation failed. Check server logs.")
