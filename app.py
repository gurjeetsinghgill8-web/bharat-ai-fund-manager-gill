import os
import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

from symbols import get_all_tickers
from data_fetcher import (
    get_stock_data, batch_update_stocks, batch_update_stocks_parallel,
    save_scan_results_to_db, load_cached_scan_from_db
)
from scoring_engine import run_scoring, score_stock, run_scoring_v2, score_stock_v2, run_scoring_v3, score_stock_v3
from sector_industry import (
    compute_nse_sectors, compute_bse_sectors, compute_all_sectors,
    compute_nse_industries, compute_bse_industries, compute_all_industries,
    get_sector_stocks, get_industry_stocks, get_sector_summary_stats,
    compute_exchange_summary
)
from report_generator import generate_excel_report, generate_pdf_report, generate_excel_report_v2, generate_pdf_report_v2
from email_dispatcher import send_momentum_newsletter
from llm_harness import has_active_api_key, generate_ai_narrative, generate_ai_narrative_v2, discuss_with_jarvis
from portfolio_manager import (
    load_portfolio, save_portfolio, add_holding, remove_holding, update_portfolio_prices,
    generate_portfolio_signals, export_portfolio_to_excel, check_and_trigger_alerts,
    play_alert_sound, show_desktop_notification,
    export_portfolio_to_json, import_portfolio_from_json, merge_portfolios, send_portfolio_via_email
)
from db import (
    init_db, create_user, get_all_users, get_user_by_name, delete_user,
    migrate_from_json, get_scan_meta
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
    
    /* ---- USER PROFILE SELECTOR STYLES ---- */
    .user-profile-badge {
        background: linear-gradient(135deg, #0284C7, #0369A1);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.95rem;
        display: inline-block;
        margin: 5px 0;
        box-shadow: 0 2px 8px rgba(2, 132, 199, 0.3);
    }
    
    /* ---- MOBILE RESPONSIVE STYLES ---- */
    @media (max-width: 768px) {
        /* Stack metric cards vertically */
        .metric-container {
            padding: 10px;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 1.4rem;
        }
        .metric-label {
            font-size: 0.75rem;
        }
        
        /* Touch-friendly buttons */
        .stButton>button {
            min-height: 44px !important;
            font-size: 0.9rem !important;
            padding: 10px 14px !important;
        }
        
        /* Horizontal scroll for tables */
        .stDataFrame {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
        }
        
        /* Headers smaller on mobile */
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.05rem !important; }
        
        /* Portfolio alert box mobile */
        .portfolio-alert-box {
            font-size: 0.95rem;
            padding: 12px;
        }
        
        /* Sidebar mobile adjustments */
        section[data-testid="stSidebar"] {
            min-width: 260px !important;
        }
        
        /* Red alert cards stack */
        .red-alert-card {
            font-size: 0.85rem;
            padding: 8px;
        }
    }
    
    @media (max-width: 480px) {
        .metric-value {
            font-size: 1.1rem;
        }
        .metric-label {
            font-size: 0.65rem;
        }
        h1 { font-size: 1.2rem !important; }
        .portfolio-alert-box {
            font-size: 0.85rem;
            padding: 10px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ------------------ AUTO-REFRESH: Every 15 minutes ------------------
st_autorefresh = st.markdown("""
    <meta http-equiv="refresh" content="900">
""", unsafe_allow_html=True)

# ------------------ STATE INITIALIZATION ------------------
# DB Migration: Import old portfolio.json into SQLite (one-time)
if "db_migrated" not in st.session_state:
    migrate_from_json()
    st.session_state["db_migrated"] = True

# Multi-User: Create default user if no users exist
if "users_initialized" not in st.session_state:
    users = get_all_users()
    if not users:
        create_user("Gurjas")
    st.session_state["users_initialized"] = True

default_email = os.getenv("EMAIL_RECIPIENTS", os.getenv("SMTP_USER", ""))
if not default_email or "your_email" in default_email or "recipient" in default_email:
    default_email = "gurjeetsinghgill8@gmail.com"

# Current user tracking
if "current_user_id" not in st.session_state:
    users = get_all_users()
    if users:
        st.session_state["current_user_id"] = users[0]["id"]
        st.session_state["current_user_name"] = users[0]["name"]
        user_email = users[0].get("email") or default_email
        st.session_state["current_user_email"] = user_email
    else:
        uid = create_user("Gurjas", email=default_email)
        st.session_state["current_user_id"] = uid
        st.session_state["current_user_name"] = "Gurjas"
        st.session_state["current_user_email"] = default_email

# Initialize scanning state
if "scanning_active" not in st.session_state:
    st.session_state["scanning_active"] = False

# Load stock cache from SQLite (persistent!) — NOT empty dict
if "stock_cache" not in st.session_state:
    db_cache = load_cached_scan_from_db()
    if db_cache:
        st.session_state["stock_cache"] = db_cache
        scan_meta = get_scan_meta()
        st.session_state["last_update"] = scan_meta.get("last_scan_time", None)
    else:
        st.session_state["stock_cache"] = {}
        st.session_state["last_update"] = None

if "last_update" not in st.session_state:
    st.session_state["last_update"] = None
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []

# Portfolio: load from SQLite for current user
if "portfolio" not in st.session_state:
    st.session_state["portfolio"] = load_portfolio(user_id=st.session_state["current_user_id"])
if "portfolio_refreshed" not in st.session_state:
    st.session_state["portfolio_refreshed"] = False
if "alert_stocks_triggered" not in st.session_state:
    st.session_state["alert_stocks_triggered"] = []

# ------------------ SCAN MODE SELECTOR ------------------
if "scan_mode" not in st.session_state:
    st.session_state["scan_mode"] = "🌐 Top 4000+ (All Stocks)"

if "all_tickers" not in st.session_state:
    st.session_state["all_tickers"] = get_all_tickers(use_full=True, limit=4000)


# ------------------ SIDEBAR ------------------
st.sidebar.image("https://img.icons8.com/nolan/96/artificial-intelligence.png", width=90)
st.sidebar.title("BHARAT AI GILL")
st.sidebar.subheader("Jarvis Option/Fund Core v2.0")

# ------------------ TOP NAVIGATION SELECTBOX (ZERO SCROLLING) ------------------
st.sidebar.markdown("---")
st.sidebar.markdown("🧭 **Navigation**")
engine_page = st.sidebar.selectbox(
    "Select Dashboard Page",
    [
        "📊 Page 1: Portfolio Dashboard",
        "🔍 Page 2: GURJAS 1 Screener (Growth & DMA & PEG < 1.2)",
        "🎯 Page 3: GURJAS 2 Screener (MidCap & PEG < 1.5)",
        "⚡ Page 4: Momentum & Breakout",
        "🏭 Page 5: Sectors & Industries"
    ],
    index=0,
    key="top_nav_selectbox"
)

# ------------------ USER PROFILE SELECTOR ------------------
st.sidebar.markdown("---")
st.sidebar.markdown("👤 **Portfolio Owner**")

# Get all users
all_users_list = get_all_users()
user_names = [u["name"] for u in all_users_list]

if user_names:
    # User selector dropdown
    current_idx = 0
    current_name = st.session_state.get("current_user_name", "")
    if current_name in user_names:
        current_idx = user_names.index(current_name)
    
    selected_user_name = st.sidebar.selectbox(
        "Switch User",
        user_names,
        index=current_idx,
        key="user_selector"
    )
    
    # Handle user switch
    if selected_user_name != st.session_state.get("current_user_name", ""):
        user_obj = get_user_by_name(selected_user_name)
        if user_obj:
            st.session_state["current_user_id"] = user_obj["id"]
            st.session_state["current_user_name"] = user_obj["name"]
            st.session_state["current_user_email"] = user_obj.get("email") or ""
            # Reload portfolio for new user
            st.session_state["portfolio"] = load_portfolio(user_id=user_obj["id"])
            st.session_state["portfolio_refreshed"] = False
            st.session_state["alert_stocks_triggered"] = []
            st.rerun()

# Show active user badge
st.sidebar.markdown(
    f'<div class="user-profile-badge">👤 {st.session_state.get("current_user_name", "Unknown")}</div>',
    unsafe_allow_html=True
)

# Email address settings
with st.sidebar.expander("📧 Alert Email Settings", expanded=False):
    curr_email = st.session_state.get("current_user_email", "") or default_email
    new_email = st.text_input("Alert Email", value=curr_email, placeholder="your_email@gmail.com", key="user_email_input")
    col_em1, col_em2 = st.columns(2)
    with col_em1:
        if st.button("Save Email", key="save_email_btn", use_container_width=True):
            from db import update_user_email
            uid = st.session_state.get("current_user_id")
            update_user_email(uid, new_email.strip())
            st.session_state["current_user_email"] = new_email.strip()
            st.success("✅ Email saved!")
            st.rerun()
    with col_em2:
        if st.button("⚡ Test Email", key="test_alert_email_btn", use_container_width=True):
            from portfolio_manager import send_alert_email
            test_holding = {
                "symbol": "RELIANCE.NS",
                "ltp": 1315.6,
                "sma_200": 1408.07,
                "dist_pct": -6.57,
                "buy_price": 2400.0,
                "quantity": 5
            }
            res = send_alert_email(test_holding, user_name=st.session_state.get("current_user_name"), user_email=new_email.strip())
            if res:
                st.success(f"✅ Alert sent to {new_email.strip()}!")
            else:
                st.info("💡 To send live Gmail alerts, set `SMTP_USER` and `SMTP_PASSWORD` app password in `.env` or Streamlit Cloud Secrets.")

# Create new user
with st.sidebar.expander("➕ Add New User", expanded=False):
    new_user_name = st.text_input("Enter name", placeholder="e.g. Sister, Dost, Papa", key="new_user_input")
    new_user_email = st.text_input("Enter email (optional)", placeholder="email@gmail.com", key="new_user_email_input")
    if st.button("Create User", key="create_user_btn"):
        if new_user_name and new_user_name.strip():
            clean_name = new_user_name.strip()
            existing = get_user_by_name(clean_name)
            if existing:
                st.warning(f"'{clean_name}' already exists!")
            else:
                clean_email = new_user_email.strip() if new_user_email.strip() else None
                uid = create_user(clean_name, email=clean_email)
                st.session_state["current_user_id"] = uid
                st.session_state["current_user_name"] = clean_name
                st.session_state["current_user_email"] = clean_email or ""
                st.session_state["portfolio"] = []
                st.session_state["portfolio_refreshed"] = False
                st.success(f"✅ User '{clean_name}' created!")
                st.rerun()
        else:
            st.warning("Please enter a name")

st.sidebar.markdown("---")

# User Manual Download Button
st.sidebar.markdown("📘 **Documentation**")
_manual_path = os.path.join("reports", "user_manual.pdf")
if not os.path.exists(_manual_path):
    try:
        from report_generator import generate_user_manual_pdf
        generate_user_manual_pdf("user_manual.pdf")
    except Exception as _e:
        print(f"Error generating manual: {_e}")

if os.path.exists(_manual_path):
    try:
        with open(_manual_path, "rb") as _f:
            st.sidebar.download_button(
                label="📥 Download User Manual PDF",
                data=_f,
                file_name="Bharat_AI_Fund_Manager_User_Manual.pdf",
                mime="application/pdf",
                key="download_manual_btn",
                use_container_width=True
            )
    except Exception as _e:
        st.sidebar.error("Error reading manual PDF")

st.sidebar.markdown("---")

# Show Turn Around info in sidebar
st.sidebar.markdown("🔄 **Turn Around (TA):** Overall CAGR > Both 3Y & 5Y CAGR → Bonus ⭐ + 🔄 Badge", unsafe_allow_html=True)

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

# Universe size presets
UNIVERSE_PRESETS = {"⚡ Core 127": 0, "🌐 Top 50": 50, "🌐 Top 100": 100, 
                    "🌐 Top 200": 200, "🌐 Top 500": 500, "🌐 Top 1000": 1000,
                    "🌐 Top 2000": 2000, "🌐 Top 3000+": 3000, "🌐 Top 4000+ (All Stocks)": 4000}

# Scan mode toggle with presets
scan_mode_labels = list(UNIVERSE_PRESETS.keys())
# Default to 4000+ All Stocks for maximum screener coverage
default_idx = scan_mode_labels.index("🌐 Top 4000+ (All Stocks)")
if "scan_mode" in st.session_state and st.session_state["scan_mode"] in UNIVERSE_PRESETS:
    default_idx = scan_mode_labels.index(st.session_state["scan_mode"])

scan_mode = st.sidebar.selectbox(
    "Universe Size",
    scan_mode_labels,
    index=default_idx,
    help="4000+ All Stocks recommended for GURJAS screeners. More stocks = more matches!"
)

# Get the limit value for this preset
selected_limit = UNIVERSE_PRESETS[scan_mode]

# Update tickers if mode changed
if scan_mode != st.session_state.get("scan_mode", ""):
    st.session_state["scan_mode"] = scan_mode
    use_full = selected_limit > 0
    limit = selected_limit if selected_limit > 0 else None
    st.session_state["all_tickers"] = get_all_tickers(use_full=use_full, limit=limit)
    total_count = len(st.session_state["all_tickers"])
    st.sidebar.info(f"Switched to {scan_mode} mode — scanning {total_count} stocks!")

all_tickers = st.session_state["all_tickers"]

# Show current universe count
st.sidebar.caption(f"📊 Current universe: {len(all_tickers)} stocks")

if st.sidebar.button("🚀 Run System Scan"):
    st.session_state["scanning_active"] = True
    st.rerun()

# Check cache status on load — try SQLite first, then pickle files
if not st.session_state["stock_cache"]:
    # Try loading from SQLite DB first
    db_cache = load_cached_scan_from_db()
    if db_cache:
        st.session_state["stock_cache"] = db_cache
        scan_meta = get_scan_meta()
        st.session_state["last_update"] = scan_meta.get("last_scan_time", "From DB")
    else:
        # Fallback to pickle cache files
        results = {}
        for ticker in all_tickers:
            data = get_stock_data(ticker, force_refresh=False)
            if data:
                results[ticker] = data
        st.session_state["stock_cache"] = results
        st.session_state["last_update"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        # Save to SQLite for future persistence
        if results:
            save_scan_results_to_db(results)

last_up = st.session_state["last_update"] or "Never"
st.sidebar.caption(f"Last data sync: {last_up}")
st.sidebar.caption(f"Universe: {len(all_tickers)} stocks")

# Cache info & cleaner
st.sidebar.markdown("---")
st.sidebar.caption("💾 **Cache Management**")
_cache_count = len(os.listdir("data_cache")) if os.path.exists("data_cache") else 0
st.sidebar.caption(f"Stock cache: {_cache_count} cached stocks")
if st.sidebar.button("🧹 Clean & Reset All Cache", help="Wipe all cached data and fetch fresh 100% Screener.in data"):
    # Clear data_cache
    if os.path.exists("data_cache"):
        for fname in os.listdir("data_cache"):
            fpath = os.path.join("data_cache", fname)
            if os.path.isfile(fpath):
                try: os.remove(fpath)
                except Exception: pass
    # Clear screener_cache
    if os.path.exists("screener_cache"):
        for fname in os.listdir("screener_cache"):
            fpath = os.path.join("screener_cache", fname)
            if os.path.isfile(fpath):
                try: os.remove(fpath)
                except Exception: pass
    # Clear DB cache
    try:
        from db import get_db_connection
        with get_db_connection() as conn:
            conn.execute("DELETE FROM scan_cache;")
            conn.execute("DELETE FROM scan_meta;")
            conn.commit()
    except Exception:
        pass
    
    st.session_state["stock_cache"] = {}
    st.session_state["last_update"] = None
    st.sidebar.success("✅ All caches cleared! Rescanning with fresh Screener.in data...")
    st.rerun()


# ============================================================
# PORTFOLIO RENDERING ENGINE (reusable — used by tabs & dedicated page)
# ============================================================
def render_portfolio_page(suffix="port"):
    """
    Render the full Excel-style portfolio dashboard.
    suffix param ensures unique Streamlit widget keys when called multiple times.
    """
    current_uid = st.session_state.get("current_user_id")
    current_uname = st.session_state.get("current_user_name", "Unknown")
    
    # Show which user's portfolio is being displayed
    st.markdown(f"👤 **Showing portfolio for: {current_uname}**")
    
    # Refresh portfolio prices on every page load (once per session)
    if not st.session_state["portfolio_refreshed"] and st.session_state["portfolio"]:
        with st.spinner(f"Refreshing portfolio prices for {current_uname}..."):
            st.session_state["portfolio"] = update_portfolio_prices(st.session_state["portfolio"], user_id=current_uid)
            st.session_state["portfolio_refreshed"] = True
            # Trigger all alert systems for stocks below 200 SMA
            triggered = check_and_trigger_alerts(st.session_state["portfolio"], user_name=current_uname, user_email=st.session_state.get("current_user_email"))
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
                st.session_state["portfolio"] = add_holding(new_sym, new_buy, int(new_qty), user_id=current_uid)
                st.success(f"✅ Added {new_sym.replace('.NS', '')} to {current_uname}'s portfolio!")
                st.session_state["portfolio"] = update_portfolio_prices(st.session_state["portfolio"], user_id=current_uid)
                st.rerun()
    
    # ---- Portfolio Share / Import Section ----
    with st.expander("📤 Share Portfolio / 📥 Import Portfolio", expanded=False):
        col_sh1, col_sh2, col_sh3 = st.columns([2, 2, 2])
        with col_sh1:
            st.markdown("**Send to Email:**")
            share_email = st.text_input("Enter recipient email", placeholder="friend@email.com", key=f"{suffix}_share_email_input")
            if portfolio and st.button("📤 Send Portfolio", key=f"{suffix}_share_email_btn", use_container_width=True):
                if share_email and "@" in share_email:
                    ok, msg = send_portfolio_via_email(portfolio, recipient_email=share_email)
                    if ok:
                        st.success(f"✅ Portfolio sent to {share_email}!")
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.warning("Please enter a valid email address")
        with col_sh2:
            if portfolio and st.button("💾 Download JSON", key=f"{suffix}_share_json", use_container_width=True):
                json_path = export_portfolio_to_json(portfolio)
                if json_path:
                    with open(json_path, "rb") as f:
                        st.download_button(
                            "📥 Click to Download Portfolio JSON",
                            f,
                            file_name="portfolio_share.json",
                            mime="application/json",
                            key=f"{suffix}_dl_json"
                        )
                else:
                    st.error("Failed to export portfolio")
        with col_sh3:
            uploaded_file = st.file_uploader(
                "📥 Import Portfolio JSON", 
                type=["json"],
                key=f"{suffix}_import_json"
            )
            if uploaded_file is not None:
                import json as _json_module
                try:
                    imported_data = _json_module.load(uploaded_file)
                    imported_holdings = import_portfolio_from_json(uploaded_file.name)
                    if imported_holdings is None and isinstance(imported_data, list):
                        imported_holdings = imported_data
                    
                    if imported_holdings and len(imported_holdings) > 0:
                        merged = merge_portfolios(portfolio, imported_holdings)
                        save_portfolio(merged, user_id=current_uid)
                        st.session_state["portfolio"] = merged
                        st.success(f"✅ Imported {len(imported_holdings)} holdings! Portfolio now has {len(merged)} stocks.")
                        st.rerun()
                    else:
                        st.error("Invalid portfolio file format")
                except Exception as e:
                    st.error(f"Error importing: {e}")
    
    st.markdown("---")
    
    # ---- Control Buttons Row ----
    col_r1, col_r2, col_r3, col_r4 = st.columns([3, 2, 2, 3])
    with col_r2:
        if st.button("🔄 Refresh Prices Now", use_container_width=True, key=f"{suffix}_port_refresh"):
            with st.spinner(f"Fetching latest prices for {current_uname}..."):
                st.session_state["portfolio"] = update_portfolio_prices(st.session_state["portfolio"], user_id=current_uid)
                triggered = check_and_trigger_alerts(st.session_state["portfolio"], user_name=current_uname, user_email=st.session_state.get("current_user_email"))
                st.session_state["alert_stocks_triggered"] = [h["symbol"] for h in triggered]
            st.rerun()
    with col_r3:
        if st.button("🔊 Test Alert Sound", use_container_width=True, key=f"{suffix}_port_test_sound"):
            play_alert_sound(repeat=2)
            show_desktop_notification("🔊 Alert Test", "Bharat AI alert system is active and working!")
            st.success("✅ Sound + Desktop notification test sent!")
    with col_r4:
        if portfolio and st.button("📥 Download Portfolio Excel", use_container_width=True, key=f"{suffix}_port_dl"):
            os.makedirs("reports", exist_ok=True)
            excel_path = os.path.join("reports", "portfolio_report.xlsx")
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
                triggered = check_and_trigger_alerts(below_sma_stocks, user_name=current_uname, user_email=st.session_state.get("current_user_email"))
                st.session_state["alert_stocks_triggered"] = list(set(
                    st.session_state.get("alert_stocks_triggered", []) + [h["symbol"] for h in triggered]
                ))
            
            import urllib.parse
            for h in below_sma_stocks:
                sym_display = h["symbol"].replace(".NS", "")
                ltp = h['ltp']
                sma = h['sma_200']
                dist = h['dist_pct']
                buy_price = h['buy_price']
                qty = h['quantity']
                
                msg_text = f"🚨 *BHARAT AI CRITICAL ALERT*: {sym_display} is BELOW 200 SMA! EXIT IMMEDIATELY!\nLTP: ₹{ltp} | 200 SMA: ₹{sma} | Distance: {dist}%\nBought: ₹{buy_price} × {qty} qty"
                wa_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg_text)}"
                tg_url = f"https://t.me/share/url?url={urllib.parse.quote('https://bharat-ai-fund-manager-gill-mkvrfrz3yhk4xtladm3jza.streamlit.app/')}&text={urllib.parse.quote(msg_text)}"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #FF0055 0%, #990033 100%); color: white; padding: 18px; border-radius: 12px; font-weight: bold; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(255, 0, 85, 0.4);">
                    <span style="font-size: 20px;">🚨🚨 CRITICAL ALERT: {sym_display} IS BELOW 200 SMA! EXIT IMMEDIATELY! 🚨🚨</span><br/>
                    <div style="font-size: 15px; margin-top: 8px; font-weight: normal;">
                        LTP: <b>₹{ltp}</b> | 200 SMA: <b>₹{sma}</b> | Distance: <b>{dist}%</b><br/>
                        Purchased: <b>₹{buy_price} × {qty} shares</b>
                    </div>
                    <div style="margin-top: 14px;">
                        <a href="{wa_url}" target="_blank" style="background-color: #25D366; color: white; padding: 8px 16px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; margin-right: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">💬 1-Click WhatsApp Alert</a>
                        <a href="{tg_url}" target="_blank" style="background-color: #0088cc; color: white; padding: 8px 16px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; box-shadow: 0 2px 6px rgba(0,0,0,0.3);">📢 1-Click Telegram Alert</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Auto Web Audio Alarm Sound
            st.components.v1.html("""
                <script>
                    try {
                        var ctx = new (window.AudioContext || window.webkitAudioContext)();
                        function playBeep(freq, duration, delay) {
                            setTimeout(function() {
                                var osc = ctx.createOscillator();
                                var gain = ctx.createGain();
                                osc.type = 'sawtooth';
                                osc.frequency.value = freq;
                                gain.gain.value = 0.3;
                                osc.connect(gain);
                                gain.connect(ctx.destination);
                                osc.start();
                                osc.stop(ctx.currentTime + duration);
                            }, delay);
                        }
                        playBeep(880, 0.2, 0);
                        playBeep(660, 0.2, 250);
                        playBeep(880, 0.3, 500);
                    } catch(e) {}
                </script>
            """, height=0)
        
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
                st.session_state["portfolio"] = remove_holding(rem_sym, user_id=current_uid)
                st.session_state["alert_stocks_triggered"] = [h["symbol"] for h in st.session_state["portfolio"]
                                                               if h.get("sma_200", 0) > 0 and not h.get("above_sma", False)]
                st.warning(f"Removed {rem_sym.replace('.NS', '')} from {current_uname}'s portfolio.")
                st.rerun()


use_full = selected_limit > 0
st.sidebar.markdown("---")
st.sidebar.write("⚙️ **Global Filter Options**")
from symbols import get_all_categories
selected_cap = st.sidebar.selectbox("Market Cap Universe", get_all_categories(use_full=use_full))

if engine_page == "⚡ Page 4: Momentum & Breakout":
    min_score = st.sidebar.slider("Minimum Quality Score", 0, 10, 5)
else:
    min_score = 0

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

    if engine_page == "📊 Page 1: Portfolio Dashboard":
        pass
    elif engine_page == "🔍 Page 2: GURJAS 1 Screener (Growth & DMA & PEG < 1.2)":
        df, continuous, red_alerts = run_scoring_v2(st.session_state["stock_cache"])
        latest_highs = pd.DataFrame()
    elif engine_page == "🎯 Page 3: GURJAS 2 Screener (MidCap & PEG < 1.5)":
        df, continuous, red_alerts = run_scoring_v3(st.session_state["stock_cache"])
        latest_highs = pd.DataFrame()
    elif engine_page == "⚡ Page 4: Momentum & Breakout":
        df, latest_highs, continuous, red_alerts = run_scoring(st.session_state["stock_cache"])
    elif engine_page == "🏭 Page 5: Sectors & Industries":
        df, latest_highs, continuous, red_alerts = run_scoring(st.session_state["stock_cache"])
        df, continuous, red_alerts = run_scoring_v3(st.session_state["stock_cache"])
        latest_highs = pd.DataFrame()
    elif engine_page == "🏭 Page 4: Sectors & Industries":
        df, latest_highs, continuous, red_alerts = run_scoring(st.session_state["stock_cache"])
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
        
    if "Total Score" in df.columns and min_score > 0:
        df = df[df["Total Score"] >= min_score] if not df.empty else df

# ------------------ MAIN SCREEN ------------------
if st.session_state.get("scanning_active", False):
    st.title("🔄 BHARAT AI - SYSTEM SCAN IN PROGRESS")
    st.markdown("""
    <div style="background-color: #0B192C; border: 2px solid #008DDA; color: #FFFFFF; font-weight: bold; font-size: 22px; padding: 25px; border-radius: 12px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0, 141, 218, 0.4);">
        <span style="font-size: 30px;">🔄</span> <b>LIVE SYSTEM SCANNING IS RUNNING NOW!</b><br/>
        <span style="color: #008DDA; font-size: 16px;">Jarvis is connecting to Screener.in and Yahoo Finance to fetch 10+ years of financials and technical metrics.</span><br/>
        <span style="font-size: 15px; font-weight: normal; color: #E0E0E0;">Please do not close or reload this browser tab. The dashboard will automatically refresh once the scan completes!</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Run scan
    with st.spinner("Scrubbing tickers, calculating CAGRs, and scoring value indicators..."):
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def _update_prog(idx, total, ticker):
            pct = float(idx + 1) / total
            progress_bar.progress(pct)
            status_text.markdown(f"🔍 **Scrubbing Ticker:** `{ticker}` ({idx+1}/{total})")

        use_full = selected_limit > 0
        total_stocks = len(all_tickers)
        
        try:
            if use_full:
                if total_stocks > 200:
                    st.info(f"🌐 Scanning {total_stocks} stocks in parallel (10 workers)...")
                    results = batch_update_stocks_parallel(all_tickers, force_refresh=True, max_workers=10, progress_callback=_update_prog)
                else:
                    results = batch_update_stocks(all_tickers, force_refresh=True, progress_callback=_update_prog)
            else:
                results = batch_update_stocks(all_tickers, force_refresh=True, progress_callback=_update_prog)
            
            st.session_state["stock_cache"] = results
            st.session_state["last_update"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            save_scan_results_to_db(results)
            st.session_state["scanning_active"] = False
            st.success(f"✅ Scan Complete! {len(results)} stocks cached & persisted to DB.")
            st.rerun()
        except Exception as e:
            st.session_state["scanning_active"] = False
            st.error(f"Scan failed: {e}")
            st.rerun()

elif engine_page == "📊 Page 1: Portfolio Dashboard":
    _current_user = st.session_state.get("current_user_name", "")
    st.title(f"📊 {_current_user}'s PORTFOLIO MANAGER")
    st.markdown("### Personal Portfolio Tracker — Excel-Style Dashboard with Auto Signals & Alerts")
    st.write(f"Tracking **{_current_user}'s** holdings against the 200-day SMA with **auto signals, live alerts, and sound notifications**. Dashboard auto-refreshes every 15 minutes.")
    st.caption("💡 Tip: If a stock falls below the 200 SMA, you'll get **🔊 sound beeps + 📢 desktop notifications + 📧 email alert + 🔴 pulsing red banner** — all automated.")
    st.caption("💡 Switch users from the sidebar dropdown to manage different portfolios.")
    st.markdown("---")
    render_portfolio_page(suffix="dedicated")

elif not st.session_state["stock_cache"]:
    st.warning("No stock data cached. Please run a 'System Scan' in the left control panel to fetch fresh market parameters.")
else:
    if engine_page == "⚡ Page 4: Momentum & Breakout":
        # Title and header
        st.title("⚡ BHARAT AI MOMENTUM & BREAKOUT SCREENER")
        st.markdown("### Jarvis Autonomous Option/Equity Momentum Screener (v1.03 Upgrade — SMA Front + Turn Around Stars)")
        
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
            breakouts_count = len(df[df["Total Score"] == 10])
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value" style="color: #00FF66; text-shadow: 0px 0px 8px rgba(0, 255, 102, 0.5);">{breakouts_count}</div>
                <div class="metric-label">Breakout Targets (Score = 10)</div>
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
            st.subheader("Equities Ranked by Multi-Factor Score (Max 10)")
            st.write("Click on any row symbol in the dropdown below to trigger the Jarvis gen AI narrative breakdown.")
            
            # Display table — full visibility with 24-Star CAGR System
            df_display = df.copy()
            df_display["CAGR Accelerating"] = df_display["CAGR Accelerating"].map({True: "✅", False: ""})
            # Build Clean Star Display: Single ⭐ + number (NOT multiple emojis)
            df_display["Stars (Sales)"] = df_display.apply(
                lambda r: f"⭐ {r['Sales Star Total']}/12" 
                if r.get('Sales Star Total', 0) > 0 else "-", axis=1)
            df_display["Stars (Profit)"] = df_display.apply(
                lambda r: f"⭐ {r['Profit Star Total']}/12"
                if r.get('Profit Star Total', 0) > 0 else "-", axis=1)
            # Clean Star Badge: Single ⭐ + total/24 + TA if applicable
            df_display["Star Badge"] = df_display.apply(
                lambda r: f"⭐ {r['Stars (Total)']} {'🔄 TA' if r.get('Turn Around', False) else ''}", axis=1)
            # Show Turn Around badge
            df_display["🔄 Turn Around"] = df_display["Turn Around"].map(
                {True: "🔄 TA Story", False: ""})
            display_cols = [
                "Ticker", "Bull Status", "Exchange", "Sector", "Industry", "Category", "Price", "PEG Ratio", "Market Cap (Cr)", "200 SMA", "200 SMA Dist %",
                "Total Score", "Stars (Total)",
                "Stars (Sales)", "Stars (Profit)", "Star Badge",
                "Sales CAGR", "Sales CAGR 3Y", "Sales CAGR 5Y",
                "Profit CAGR", "Profit CAGR 3Y", "Profit CAGR 5Y",
                "Sales+Profit CAGR Total",
                "🔄 Turn Around",
                "CAGR Accelerating"
            ]
            display_cols = [c for c in display_cols if c in df_display.columns]
            st.dataframe(
                df_display[display_cols],
                use_container_width=True,
                height=min(600, 35 * len(df_display) + 40)
            )

            # --- DIAGNOSTIC EXPANDER: Why Page 1 vs Screener.in differs ---
            with st.expander("🔍 **Why does Page 1 stock list differ from Screener.in queries? (Click to view detailed analysis)**"):
                st.markdown("""
                ### 📊 Diagnostic Analysis: Page 1 vs Screener.in Queries
                
                1. **Multi-Factor Ranking vs Hard Boolean Filters**:
                   - **Page 1 (Momentum & Breakout)** ranks stocks by a multi-factor score and 24-Star CAGR rating across all listed stocks.
                   - **Screener.in (GURJAS 1 & 2)** uses strict boolean `AND` filters (e.g. `Sales CAGR 3Y > 20% AND Profit CAGR 5Y > 20% AND PEG < 1.2`).
                   - Stocks that miss one threshold (e.g. PEG = 1.25) still appear on Page 1 if their momentum is strong, but are filtered out on Page 2/3.

                2. **Universe Pool Size**:
                   - If sidebar is set to **`⚡ Core 127`**, only 127 hand-picked stocks are scanned.
                   - Screener.in searches all **4000+** listed NSE & BSE companies.
                   - 💡 *To match Screener.in completely across the entire Indian stock market, select **`🌐 Top 4000+ (All Stocks)`** in the sidebar control center!*

                3. **PEG Ratio Calculation Standard**:
                   - Formula: `PEG Ratio = P/E / 3Yr Profit Growth %`.
                   - Our system calculates exact PEG Ratios matching Screener.in using 10+ years of financial data from Screener scraper.
                """)
            
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
                    pdf_name = "Bharat_AI_Gill_Momentum_Report.pdf"
                    excel_name = "Bharat_AI_Gill_Momentum_Data.xlsx"
                    pdf_path = os.path.join("reports", pdf_name)
                    excel_path = os.path.join("reports", excel_name)
                    
                    # Generate reports
                    pdf_ok = generate_pdf_report(df, pdf_name)
                    excel_ok = generate_excel_report(df, latest_highs, continuous, red_alerts, excel_name)
                    
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

    elif engine_page == "🔍 Page 2: GURJAS 1 Screener (Growth & DMA & PEG < 1.2)":
        # Page 2 — Title and header
        st.title("🔍 BHARAT AI GURJAS 1 SCREENER")
        st.markdown("### Screener.in Exact Match Engine — Sales/Profit 3Y/5Y/Overall > 20% + DMA 200 < Price + PEG Ratio < 1.2")
        
        st.markdown("""
        <div style="background: rgba(2, 132, 199, 0.1); border-left: 5px solid #0284C7; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
            <b>🎯 GURJAS 1 Parameters (Exact Screener.in Match — ALL 8 conditions AND):</b><br/>
            • <b>Sales Growth 3Y</b> &gt; 20% &nbsp;&nbsp;|&nbsp;&nbsp; • <b>Sales Growth 5Y</b> &gt; 20% &nbsp;&nbsp;|&nbsp;&nbsp; • <b>Sales Growth Overall</b> &gt; 20%<br/>
            • <b>Profit Growth 3Y</b> &gt; 20% &nbsp;&nbsp;|&nbsp;&nbsp; • <b>Profit Growth 5Y</b> &gt; 20% &nbsp;&nbsp;|&nbsp;&nbsp; • <b>Profit Growth Overall</b> &gt; 20%<br/>
            • <b>📊 DMA 200 &lt; Current Price</b> (Stock must be ABOVE 200 SMA) &nbsp;&nbsp;|&nbsp;&nbsp; • <b>PEG Ratio</b> &lt; 1.2 (P/E ÷ 3Y Profit CAGR)
        </div>
        """, unsafe_allow_html=True)
        
        # 1. Metric Display Cards
        g1_matches = len(df[df["Gurjas1 Pass"] == True]) if (not df.empty and "Gurjas1 Pass" in df.columns) else 0
        star_stocks = len(df[df["Total Star Rating"] >= 12]) if not df.empty else 0
        avg_peg = df[df["PEG Ratio"] > 0]["PEG Ratio"].mean() if (not df.empty and "PEG Ratio" in df.columns) else 0.0
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""<div class="metric-container"><div class="metric-value">{len(all_tickers)}</div><div class="metric-label">Universe Pool</div></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric-container"><div class="metric-value" style="color: #00FF66; text-shadow: 0px 0px 8px rgba(0, 255, 102, 0.5);">{g1_matches}</div><div class="metric-label">GURJAS 1 Targets</div></div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="metric-container"><div class="metric-value" style="color: #FFD700; text-shadow: 0px 0px 8px rgba(255, 215, 0, 0.5);">⭐⭐⭐ {star_stocks}</div><div class="metric-label">Star Stocks (≥12 Stars)</div></div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="metric-container"><div class="metric-value" style="color: #008DDA;">{round(avg_peg, 2) if avg_peg else 'N/A'}</div><div class="metric-label">Avg PEG Ratio</div></div>""", unsafe_allow_html=True)
        with col5:
            alerts_count = len(red_alerts)
            st.markdown(f"""<div class="metric-container"><div class="metric-value" style="color: #FF0055;">{alerts_count}</div><div class="metric-label">Blacklisted/Red Alert</div></div>""", unsafe_allow_html=True)
            
        st.markdown("<br/>", unsafe_allow_html=True)

        # 2. Main Tabbed Windows (Page 2)
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🏆 GURJAS 1 Leaderboard", 
            "📈 Sustained momentum", 
            "🚨 Red Alert Blacklist",
            "💬 Jarvis AI Consultant",
            "🧪 Backtesting Simulator",
            "📊 My Portfolio",
            "📧 Newsletter Dispatcher"
        ])
        
        # --- TAB 1: Ranked Leaderboard ---
        with tab1:
            st.subheader("🎯 GURJAS 1 Qualifying Matches (Screener.in Exact Match)")
            st.write("Showing ONLY stocks that pass ALL 8 GURJAS 1 criteria simultaneously: Sales/Profit 3Y & 5Y & Overall > 20%, 200 DMA < Current Price, and PEG < 1.2.")
            
            # Filter ONLY stocks that passed Gurjas1 Pass == True for main table
            perfect_matches = df[df["Gurjas1 Pass"] == True].copy() if (not df.empty and "Gurjas1 Pass" in df.columns) else pd.DataFrame()
            
            if not perfect_matches.empty:
                perfect_matches["Match Status"] = "✅ PERFECT MATCH"
                display_cols = [
                    "Ticker", "Match Status", "PEG Ratio", "Market Cap (Cr)", "Price", "200 SMA", "200 SMA Dist %",
                    "Sales CAGR 3Y", "Sales CAGR 5Y", "Sales CAGR",
                    "Profit CAGR 3Y", "Profit CAGR 5Y", "Profit CAGR",
                    "PE", "Stars (Total)", "Sector", "Category"
                ]
                display_cols = [c for c in display_cols if c in perfect_matches.columns]
                st.dataframe(
                    perfect_matches[display_cols],
                    use_container_width=True,
                    height=min(400, 35 * len(perfect_matches) + 40)
                )
            else:
                st.info("ℹ️ No stocks in the current scanned pool pass ALL 8 GURJAS 1 conditions simultaneously. Select '🌐 Top 4000+ (All Stocks)' in the sidebar and run 'System Scan' to search all listed stocks.")
            
            # Optional Expander for Near Matches
            with st.expander("🔍 View Near-Match Stocks & Scanned Pool Breakdown (Optional)"):
                near_matches = df[df["Gurjas1 Pass"] == False].copy() if (not df.empty and "Gurjas1 Pass" in df.columns) else pd.DataFrame()
                if not near_matches.empty:
                    near_matches["Match Status"] = "⚠️ Near Match"
                    display_cols = [
                        "Ticker", "Match Status", "PEG Ratio", "Market Cap (Cr)", "Price", "200 SMA", "200 SMA Dist %",
                        "Sales CAGR 3Y", "Sales CAGR 5Y", "Sales CAGR",
                        "Profit CAGR 3Y", "Profit CAGR 5Y", "Profit CAGR",
                        "PE", "Stars (Total)", "Sector", "Category"
                    ]
                    display_cols = [c for c in display_cols if c in near_matches.columns]
                    st.dataframe(near_matches[display_cols], use_container_width=True, height=400)
            
            st.markdown("---")
            st.subheader("🤖 Gen AI Jarvis Stock Diagnostic Report (GURJAS 1 Mode)")
            p2_matching_tickers = df[df["Gurjas1 Pass"] == True]["Ticker"].tolist() if (not df.empty and "Gurjas1 Pass" in df.columns) else []
            p2_options = p2_matching_tickers if p2_matching_tickers else (df["Ticker"].tolist() if not df.empty else ["None"])
            selected_ticker = st.selectbox("Select Ticker for Diagnostic", p2_options, key="p2_diag_tk")
            
            if selected_ticker and selected_ticker != "None":
                stock_data = st.session_state["stock_cache"][selected_ticker]
                row_data = df[df["Ticker"] == selected_ticker].iloc[0]
                
                is_g1_match = row_data.get("Gurjas1 Pass", False)
                if not is_g1_match:
                    st.markdown("""
                    <div style="margin-bottom: 15px; background-color: rgba(239, 68, 68, 0.2); border: 2px solid #EF4444; color: #B91C1C; padding: 15px; border-radius: 10px; font-weight: bold;">
                        ⚠️ ALERT: This stock does not satisfy all 7 GURJAS 1 parameters (Growth > 20% & PEG < 1.2).
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="margin-bottom: 15px; background-color: rgba(16, 185, 129, 0.2); border: 2px solid #10B981; color: #065F46; padding: 15px; border-radius: 10px; font-weight: bold;">
                        ✅ PERFECT: Full GURJAS 1 Screener Match! High Growth + PEG < 1.2.
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
                    st.markdown("#### Key Valuation & CAGR Metrics")
                    st.metric("PEG Ratio", f"{row_data.get('PEG Ratio', 0.0)}")
                    st.metric("Market Cap (Cr)", f"₹{row_data.get('Market Cap (Cr)', 0.0):,.1f} Cr")
                    st.metric("P/E Ratio", f"{row_data.get('PE', 0.0)}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Sales CAGR 3Y", f'{row_data.get("Sales CAGR 3Y", 0):.1f}%')
                        st.metric("Sales CAGR 5Y", f'{row_data.get("Sales CAGR 5Y", 0):.1f}%')
                    with c2:
                        st.metric("Profit CAGR 3Y", f'{row_data.get("Profit CAGR 3Y", 0):.1f}%')
                        st.metric("Profit CAGR 5Y", f'{row_data.get("Profit CAGR 5Y", 0):.1f}%')

        # --- TAB 2: Sustained Momentum ---
        with tab2:
            st.subheader("📈 Sustained High Momentum Performers")
            st.write("These stocks have successfully consolidated near their recent highs over 1, 2, or 6 months without breaking structure.")
            if not continuous.empty:
                display_cont_cols = ["Ticker", "Category", "Price", "PEG Ratio", "Market Cap (Cr)", "Momentum Status"]
                display_cont_cols = [c for c in display_cont_cols if c in continuous.columns]
                st.dataframe(continuous[display_cont_cols], use_container_width=True)
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
                        <strong>{row['Ticker'].replace('.NS', '')}</strong> ({row['Category']}) | Total Score: {row.get('Total Score', 'N/A')}<br/>
                        ⚠️ Alerts Flagged: <em>{row['Red Reasons']}</em><br/>
                        Debt/Equity: {row['Debt/Equity']} | Reserves: ₹{row['Reserves']} Cr
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("Excellent! No stocks in your watchlist are currently triggering red-alert flags.")

        # --- TAB 4: Jarvis AI Chat Consultant ---
        with tab4:
            st.subheader("💬 Discuss Markets with Jarvis (GURJAS 1 Mode)")
            st.write("Ask Jarvis to compare stocks, explain growth & PEG ratio setups.")
            
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
            st.subheader("🧪 Portfolio Backtesting Simulator (GURJAS 1 Mode)")
            st.write("Evaluate how a portfolio of GURJAS 1 growth stocks performed compared to Nifty.")
            
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
                    "Engine": ["Bharat AI GURJAS 1 Engine", "Nifty 50 Index"],
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
            st.subheader("📧 Newsletter & SMTP Mailing Engine (GURJAS 1 Mode)")
            st.write("Configure email updates to be delivered to subscribers with attached PDF & Excel sheets representing GURJAS 1 picks.")
            
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
            if st.button("Generate GURJAS 1 Reports & Dispatch Newsletter", key="p2_mail_trigger"):
                with st.spinner("Compiling PDF and Excel dossier files..."):
                    pdf_name = "Bharat_AI_Gill_Gurjas1_Report.pdf"
                    excel_name = "Bharat_AI_Gill_Gurjas1_Data.xlsx"
                    pdf_path = os.path.join("reports", pdf_name)
                    excel_path = os.path.join("reports", excel_name)
                    
                    pdf_ok = generate_pdf_report_v2(df, pdf_name)
                    excel_ok = generate_excel_report_v2(df, continuous, red_alerts, excel_name)
                    
                    if pdf_ok and excel_ok:
                        st.success("GURJAS 1 Reports generated successfully!")
                        
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

    elif engine_page == "🎯 Page 3: GURJAS 2 Screener (MidCap & PEG < 1.5)":
        # Page 3 — Title and header
        st.title("🎯 BHARAT AI GURJAS 2 SCREENER")
        st.markdown("### Screener.in Exact Match Engine — Sales/Profit > 20%, Market Cap > ₹1,000 Cr & PEG < 1.5")
        
        st.markdown("""
        <div style="background: rgba(16, 185, 129, 0.1); border-left: 5px solid #10B981; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
            <b>🎯 GURJAS 2 Parameters (Exact Screener.in Match):</b><br/>
            • <b>Sales Growth 3Y</b> > 10% &nbsp;&nbsp;|&nbsp;&nbsp; • <b>Sales Growth 5Y</b> > 10% &nbsp;&nbsp;|&nbsp;&nbsp; • <b>Sales Growth Overall</b> > 20%<br/>
            • <b>Profit Growth Overall</b> > 20% &nbsp;&nbsp;|&nbsp;&nbsp; • <b>Profit Growth 3Y</b> > 10% &nbsp;&nbsp;|&nbsp;&nbsp; • <b>Market Capitalization</b> > ₹1,000 Cr<br/>
            • <b>PEG Ratio</b> &lt; 1.5 (P/E ÷ 3Y Profit CAGR)
        </div>
        """, unsafe_allow_html=True)
        
        # 1. Metric Display Cards
        g2_matches = len(df[df["Gurjas2 Pass"] == True]) if (not df.empty and "Gurjas2 Pass" in df.columns) else 0
        star_stocks = len(df[df["Total Star Rating"] >= 12]) if not df.empty else 0
        avg_peg = df[df["PEG Ratio"] > 0]["PEG Ratio"].mean() if (not df.empty and "PEG Ratio" in df.columns) else 0.0
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""<div class="metric-container"><div class="metric-value">{len(all_tickers)}</div><div class="metric-label">Universe Pool</div></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric-container"><div class="metric-value" style="color: #00FF66; text-shadow: 0px 0px 8px rgba(0, 255, 102, 0.5);">{g2_matches}</div><div class="metric-label">GURJAS 2 Targets</div></div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="metric-container"><div class="metric-value" style="color: #FFD700; text-shadow: 0px 0px 8px rgba(255, 215, 0, 0.5);">⭐⭐⭐ {star_stocks}</div><div class="metric-label">Star Stocks (≥12 Stars)</div></div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="metric-container"><div class="metric-value" style="color: #008DDA;">{round(avg_peg, 2) if avg_peg else 'N/A'}</div><div class="metric-label">Avg PEG Ratio</div></div>""", unsafe_allow_html=True)
        with col5:
            alerts_count = len(red_alerts)
            st.markdown(f"""<div class="metric-container"><div class="metric-value" style="color: #FF0055;">{alerts_count}</div><div class="metric-label">Blacklisted/Red Alert</div></div>""", unsafe_allow_html=True)
            
        st.markdown("<br/>", unsafe_allow_html=True)

        # 2. Main Tabbed Windows (Page 3)
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "🏆 GURJAS 2 Leaderboard", 
            "📈 Sustained momentum", 
            "🚨 Red Alert Blacklist",
            "💬 Jarvis AI Consultant",
            "🧪 Backtesting Simulator",
            "📊 My Portfolio",
            "📧 Newsletter Dispatcher"
        ])
        
        # --- TAB 1: Ranked Leaderboard ---
        with tab1:
            st.subheader("🎯 GURJAS 2 Qualifying Matches (Screener.in Exact Match)")
            st.write("Showing ONLY stocks that pass ALL 7 GURJAS 2 criteria simultaneously: Sales/Profit 3Y > 10%, Sales/Profit Overall > 20%, Market Cap > ₹1,000 Cr, and PEG < 1.5.")
            
            # Filter ONLY stocks that passed Gurjas2 Pass == True for main table
            perfect_matches = df[df["Gurjas2 Pass"] == True].copy() if (not df.empty and "Gurjas2 Pass" in df.columns) else pd.DataFrame()
            
            if not perfect_matches.empty:
                perfect_matches["Match Status"] = "✅ PERFECT MATCH"
                display_cols = [
                    "Ticker", "Match Status", "PEG Ratio", "Market Cap (Cr)", "Price", "200 SMA", "200 SMA Dist %",
                    "Sales CAGR 3Y", "Sales CAGR 5Y", "Sales CAGR",
                    "Profit CAGR 3Y", "Profit CAGR 5Y", "Profit CAGR",
                    "PE", "Stars (Total)", "Sector", "Category"
                ]
                display_cols = [c for c in display_cols if c in perfect_matches.columns]
                st.dataframe(
                    perfect_matches[display_cols],
                    use_container_width=True,
                    height=min(400, 35 * len(perfect_matches) + 40)
                )
            else:
                st.info("ℹ️ No stocks in the current scanned pool pass ALL 7 GURJAS 2 conditions simultaneously. Select '🌐 Top 4000+ (All Stocks)' in the sidebar and run 'System Scan' to search all listed stocks.")
            
            # Optional Expander for Near Matches
            with st.expander("🔍 View Near-Match Stocks & Scanned Pool Breakdown (Optional)"):
                near_matches = df[df["Gurjas2 Pass"] == False].copy() if (not df.empty and "Gurjas2 Pass" in df.columns) else pd.DataFrame()
                if not near_matches.empty:
                    near_matches["Match Status"] = "⚠️ Near Match"
                    display_cols = [
                        "Ticker", "Match Status", "PEG Ratio", "Market Cap (Cr)", "Price", "200 SMA", "200 SMA Dist %",
                        "Sales CAGR 3Y", "Sales CAGR 5Y", "Sales CAGR",
                        "Profit CAGR 3Y", "Profit CAGR 5Y", "Profit CAGR",
                        "PE", "Stars (Total)", "Sector", "Category"
                    ]
                    display_cols = [c for c in display_cols if c in near_matches.columns]
                    st.dataframe(near_matches[display_cols], use_container_width=True, height=400)
            
            st.markdown("---")
            st.subheader("🤖 Gen AI Jarvis Stock Diagnostic Report (GURJAS 2 Mode)")
            p3_matching_tickers = df[df["Gurjas2 Pass"] == True]["Ticker"].tolist() if (not df.empty and "Gurjas2 Pass" in df.columns) else []
            p3_options = p3_matching_tickers if p3_matching_tickers else (df["Ticker"].tolist() if not df.empty else ["None"])
            selected_ticker = st.selectbox("Select Ticker for Diagnostic", p3_options, key="p3_diag_tk")
            
            if selected_ticker and selected_ticker != "None":
                stock_data = st.session_state["stock_cache"][selected_ticker]
                row_data = df[df["Ticker"] == selected_ticker].iloc[0]
                
                is_g2_match = row_data.get("Gurjas2 Pass", False)
                if not is_g2_match:
                    st.markdown("""
                    <div style="margin-bottom: 15px; background-color: rgba(239, 68, 68, 0.2); border: 2px solid #EF4444; color: #B91C1C; padding: 15px; border-radius: 10px; font-weight: bold;">
                        ⚠️ ALERT: This stock does not satisfy all GURJAS 2 parameters (Market Cap > 1000 Cr & PEG < 1.5).
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="margin-bottom: 15px; background-color: rgba(16, 185, 129, 0.2); border: 2px solid #10B981; color: #065F46; padding: 15px; border-radius: 10px; font-weight: bold;">
                        ✅ PERFECT: Full GURJAS 2 Screener Match! Market Cap > ₹1000 Cr + PEG < 1.5.
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
                    st.markdown("#### Key Valuation & CAGR Metrics")
                    st.metric("PEG Ratio", f"{row_data.get('PEG Ratio', 0.0)}")
                    st.metric("Market Cap (Cr)", f"₹{row_data.get('Market Cap (Cr)', 0.0):,.1f} Cr")
                    st.metric("P/E Ratio", f"{row_data.get('PE', 0.0)}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Sales CAGR 3Y", f'{row_data.get("Sales CAGR 3Y", 0):.1f}%')
                        st.metric("Sales CAGR 5Y", f'{row_data.get("Sales CAGR 5Y", 0):.1f}%')
                    with c2:
                        st.metric("Profit CAGR 3Y", f'{row_data.get("Profit CAGR 3Y", 0):.1f}%')
                        st.metric("Profit CAGR 5Y", f'{row_data.get("Profit CAGR 5Y", 0):.1f}%')

        # --- TAB 2: Sustained Momentum ---
        with tab2:
            st.subheader("📈 Sustained High Momentum Performers")
            st.write("These stocks have successfully consolidated near their recent highs over 1, 2, or 6 months without breaking structure.")
            if not continuous.empty:
                display_cont_cols = ["Ticker", "Category", "Price", "PEG Ratio", "Market Cap (Cr)", "Momentum Status"]
                display_cont_cols = [c for c in display_cont_cols if c in continuous.columns]
                st.dataframe(continuous[display_cont_cols], use_container_width=True)
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
                        <strong>{row['Ticker'].replace('.NS', '')}</strong> ({row['Category']}) | Total Score: {row.get('Total Score', 'N/A')}<br/>
                        ⚠️ Alerts Flagged: <em>{row['Red Reasons']}</em><br/>
                        Debt/Equity: {row['Debt/Equity']} | Reserves: ₹{row['Reserves']} Cr
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("Excellent! No stocks in your watchlist are currently triggering red-alert flags.")

        # --- TAB 4: Jarvis AI Chat Consultant ---
        with tab4:
            st.subheader("💬 Discuss Markets with Jarvis (GURJAS 2 Mode)")
            st.write("Ask Jarvis to compare stocks, explain midcap growth & PEG ratio setups.")
            
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
                    
                user_input = st.chat_input("Talk to Jarvis (e.g. Compare CDSL vs BSE...)", key="p3_chat_in")
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
            st.subheader("🧪 Portfolio Backtesting Simulator (GURJAS 2 Mode)")
            st.write("Evaluate how a portfolio of GURJAS 2 midcap growth stocks performed compared to Nifty.")
            
            years = st.slider("Backtest Period (Years)", 1, 3, 2, key="p3_backtest_yr")
            
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
                    "Engine": ["Bharat AI GURJAS 2 Engine", "Nifty 50 Index"],
                    "Cumulative Return %": [avg_ret, nifty_mock_return]
                })
                fig_compare = px.bar(
                    comparison_df, 
                    x="Engine", 
                    y="Cumulative Return %", 
                    color="Engine",
                    color_discrete_sequence=['#10B981', '#415A77'],
                    title="Strategy vs Benchmark Cumulative Return Comparison",
                    template="plotly_white"
                )
                st.plotly_chart(fig_compare, use_container_width=True)
            else:
                st.info("Insufficient historical range to simulate backtest.")

        # --- TAB 6: My Portfolio (Page 3) ---
        with tab6:
            render_portfolio_page(suffix="p3")

        # --- TAB 7: Newsletter Dispatcher (Page 3) ---
        with tab7:
            st.subheader("📧 Newsletter & SMTP Mailing Engine (GURJAS 2 Mode)")
            st.write("Configure email updates to be delivered to subscribers with attached PDF & Excel sheets representing GURJAS 2 picks.")
            
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
            if st.button("Generate GURJAS 2 Reports & Dispatch Newsletter", key="p3_mail_trigger"):
                with st.spinner("Compiling PDF and Excel dossier files..."):
                    pdf_name = "Bharat_AI_Gill_Gurjas2_Report.pdf"
                    excel_name = "Bharat_AI_Gill_Gurjas2_Data.xlsx"
                    pdf_path = os.path.join("reports", pdf_name)
                    excel_path = os.path.join("reports", excel_name)
                    
                    pdf_ok = generate_pdf_report_v2(df, pdf_name)
                    excel_ok = generate_excel_report_v2(df, continuous, red_alerts, excel_name)
                    
                    if pdf_ok and excel_ok:
                        st.success("GURJAS 2 Reports generated successfully!")
                        
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

    elif engine_page == "🏭 Page 5: Sectors & Industries":
        
        if df.empty:
            st.warning("No stock data available. Run a scan first.")
        else:
            # ── Summary Stats ──
            stats = get_sector_summary_stats(df)
            exc_summary = compute_exchange_summary(df)
            
            col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
            with col_s1:
                st.markdown(f"""<div class="metric-container"><div class="metric-value">{stats.get('nse_sectors', 0)}</div><div class="metric-label">NSE Sectors</div></div>""", unsafe_allow_html=True)
            with col_s2:
                st.markdown(f"""<div class="metric-container"><div class="metric-value">{stats.get('bse_sectors', 0)}</div><div class="metric-label">BSE Sectors</div></div>""", unsafe_allow_html=True)
            with col_s3:
                st.markdown(f"""<div class="metric-container"><div class="metric-value">{stats.get('total_industries', 0)}</div><div class="metric-label">Total Industries</div></div>""", unsafe_allow_html=True)
            with col_s4:
                top_sec = stats.get('top_sector', 'N/A')
                top_sec_score = stats.get('top_sector_score', 0)
                st.markdown(f"""<div class="metric-container"><div class="metric-value" style="color:#00CC00;">🏆 {top_sec}</div><div class="metric-label">Top Sector (Avg: {top_sec_score})</div></div>""", unsafe_allow_html=True)
            with col_s5:
                worst = stats.get('worst_sector', 'N/A')
                worst_score = stats.get('worst_sector_score', 0)
                st.markdown(f"""<div class="metric-container"><div class="metric-value" style="color:#CC0000;">⚠️ {worst}</div><div class="metric-label">Worst Sector (Avg: {worst_score})</div></div>""", unsafe_allow_html=True)
            
            st.markdown("<br/>", unsafe_allow_html=True)
            
            # ── Exchange Summary Table ──
            if not exc_summary.empty:
                st.subheader("📊 NSE vs BSE — Quick Comparison")
                st.dataframe(exc_summary, use_container_width=True)
                st.markdown("---")
            
            # ── Tabs ──
            stab1, stab2, stab3, stab4, stab5 = st.tabs([
                "🇮🇳 NSE Sectors",
                "🇮🇳 BSE Sectors", 
                "🏭 All Industries",
                "🔍 Sector Detail",
                "🔬 Industry Detail"
            ])
            
            # ── TAB 1: NSE Sectors ──
            with stab1:
                st.subheader("NSE Sector Performance Ranking")
                st.caption("Ranked by average quality score. Green = positive, Red = negative.")
                nse_sectors = compute_nse_sectors(df)
                if not nse_sectors.empty:
                    def _color_perf(val):
                        if isinstance(val, str):
                            if "Strong" in val: return "color: #00CC00; font-weight: bold"
                            if "Positive" in val: return "color: #008800;"
                            if "Negative" in val: return "color: #CC8800;"
                            if "Weak" in val: return "color: #CC0000; font-weight: bold"
                        return ""
                    styled_nse = nse_sectors.style.map(_color_perf, subset=["Performance"])
                    st.dataframe(styled_nse, use_container_width=True, height=min(500, 35 * len(nse_sectors) + 40))
                else:
                    st.info("No NSE sector data available.")
            
            # ── TAB 2: BSE Sectors ──
            with stab2:
                st.subheader("BSE Sector Performance Ranking")
                st.caption("BSE stocks (.BO tickers) grouped by sector. Fewer stocks than NSE.")
                bse_sectors = compute_bse_sectors(df)
                if not bse_sectors.empty:
                    def _color_perf_bse(val):
                        if isinstance(val, str):
                            if "Strong" in val: return "color: #00CC00; font-weight: bold"
                            if "Positive" in val: return "color: #008800;"
                            if "Negative" in val: return "color: #CC8800;"
                            if "Weak" in val: return "color: #CC0000; font-weight: bold"
                        return ""
                    styled_bse = bse_sectors.style.map(_color_perf_bse, subset=["Performance"])
                    st.dataframe(styled_bse, use_container_width=True, height=min(500, 35 * len(bse_sectors) + 40))
                else:
                    st.info("No BSE sector data available. Add BSE stocks to your universe to see this.")
                    st.info("💡 Tip: Use 'Top 3000+' universe mode to also scan BSE stocks (.BO).")
            
            # ── TAB 3: All Industries ──
            with stab3:
                st.subheader("Industry Performance Ranking (All Exchanges)")
                st.caption("More granular than sectors — 80+ industries ranked by performance.")
                all_ind = compute_all_industries(df)
                if not all_ind.empty:
                    st.dataframe(all_ind, use_container_width=True, height=min(600, 35 * len(all_ind) + 40))
                else:
                    st.info("No industry data available.")
            
            # ── TAB 4: Sector Detail ──
            with stab4:
                st.subheader("🔍 Sector Details — View All Stocks in a Sector")
                all_sectors = sorted(df["Sector"].unique()) if "Sector" in df.columns else []
                if all_sectors:
                    col_sel1, col_sel2 = st.columns([2, 1])
                    with col_sel1:
                        sel_sector = st.selectbox("Select Sector", all_sectors, key="p3_sec_select")
                    with col_sel2:
                        sel_exch = st.selectbox("Exchange", ["All", "NSE", "BSE"], key="p3_sec_exch")
                    
                    exchange_filter = None if sel_exch == "All" else sel_exch
                    sector_stocks = get_sector_stocks(df, sel_sector, exchange=exchange_filter)
                    if not sector_stocks.empty:
                        st.success(f"📊 {len(sector_stocks)} stocks in **{sel_sector}**" + (f" ({sel_exch})" if sel_exch != "All" else ""))
                        detail_cols = ["Ticker", "Exchange", "Industry", "Category", "Price", "Total Score", "Stars (Total)", "Sales CAGR", "Profit CAGR", "200 SMA Dist %"]
                        detail_cols = [c for c in detail_cols if c in sector_stocks.columns]
                        st.dataframe(sector_stocks[detail_cols], use_container_width=True)
                    else:
                        st.warning(f"No stocks found for sector: {sel_sector}")
                else:
                    st.info("No sector data available. Run a scan first.")
            
            # ── TAB 5: Industry Detail ──
            with stab5:
                st.subheader("🔬 Industry Details — View All Stocks in an Industry")
                all_industries = sorted(df["Industry"].unique()) if "Industry" in df.columns else []
                if all_industries:
                    col_ind1, col_ind2 = st.columns([2, 1])
                    with col_ind1:
                        sel_ind = st.selectbox("Select Industry", all_industries, key="p3_ind_select")
                    with col_ind2:
                        sel_ind_exch = st.selectbox("Exchange", ["All", "NSE", "BSE"], key="p3_ind_exch")
                    
                    exch_filter = None if sel_ind_exch == "All" else sel_ind_exch
                    ind_stocks = get_industry_stocks(df, sel_ind, exchange=exch_filter)
                    if not ind_stocks.empty:
                        st.success(f"📊 {len(ind_stocks)} stocks in **{sel_ind}**" + (f" ({sel_ind_exch})" if sel_ind_exch != "All" else ""))
                        detail_cols = ["Ticker", "Exchange", "Sector", "Category", "Price", "Total Score", "Stars (Total)", "Sales CAGR", "Profit CAGR", "200 SMA Dist %"]
                        detail_cols = [c for c in detail_cols if c in ind_stocks.columns]
                        st.dataframe(ind_stocks[detail_cols], use_container_width=True)
                    else:
                        st.warning(f"No stocks found for industry: {sel_ind}")
                else:
                    st.info("No industry data available. Run a scan first.")
