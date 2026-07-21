"""
llm_harness.py — JARVIS AI BRAIN v2.0
══════════════════════════════════════════════════════════════
Dual-Provider LLM Harness with Auto-Failover

Key Features:
  - Reads keys from: jarvis_keys.txt → .env → Windows System Environment Variables
  - Provider order: Groq → xAI/Grok → Gemini → Local Fallback
  - Works 24/7 even when laptop is closed (via System Environment Variables)
  - Auto-failover: if one provider fails, next one is tried automatically

How to set System Environment Variables for 24/7 operation:
  Press Win+R → sysdm.cpl → Advanced → Environment Variables → System variables → New
  - Variable: JARVIS_GROQ_KEY    Value: gsk_your_groq_key
  - Variable: JARVIS_XAI_KEY     Value: xai_your_xai_key
  - Variable: JARVIS_GEMINI_KEY  Value: AIzaSy_your_gemini_key
══════════════════════════════════════════════════════════════
"""
import os
import json
import requests
from dotenv import load_dotenv

# Get the directory where THIS script lives (works from ANY working directory)
_HERE = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(_HERE, ".env"))

# ══════════════════════════════════════════════════════════════
# KEY LOADER — Reads from 3 sources in priority order
# ══════════════════════════════════════════════════════════════

def _read_jarvis_keys_file():
    """Parse jarvis_keys.txt and return a dict of keys found."""
    keys = {}
    # Try script directory first, then CWD
    possible_paths = [
        os.path.join(_HERE, "jarvis_keys.txt"),
        os.path.join(os.getcwd(), "jarvis_keys.txt"),
    ]
    for filepath in possible_paths:
        try:
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            parts = line.split("=", 1)
                            key_name = parts[0].strip()
                            key_val = parts[1].strip()
                            if key_val and len(key_val) > 5:
                                keys[key_name] = key_val
                break  # Found file, stop searching
        except Exception:
            pass
    return keys


def _load_api_key_from_env(key_name):
    """Try to load a key from .env file."""
    return os.getenv(key_name, "").strip()


def _load_api_key_from_system(key_name):
    """Try to load a key from Windows System Environment Variables.
    These persist even when laptop is closed and work in background/VPS mode.
    """
    system_var_map = {
        "GROQ_API_KEY": "JARVIS_GROQ_KEY",
        "XAI_API_KEY": "JARVIS_XAI_KEY",
        "GEMINI_API_KEY": "JARVIS_GEMINI_KEY",
    }
    sys_var = system_var_map.get(key_name)
    if sys_var:
        return os.environ.get(sys_var, "").strip()
    return ""


def _load_api_key_from_streamlit_secrets(key_name):
    """Try to load a key from Streamlit Cloud Secrets."""
    try:
        import streamlit as st
        # Check direct key name first
        val = st.secrets.get(key_name, "")
        if val:
            return val
        # Then check JARVIS_GROQ_KEY etc.
        system_var_map = {
            "GROQ_API_KEY": "JARVIS_GROQ_KEY",
            "XAI_API_KEY": "JARVIS_XAI_KEY",
            "GEMINI_API_KEY": "JARVIS_GEMINI_KEY",
        }
        sys_var = system_var_map.get(key_name)
        if sys_var:
            return st.secrets.get(sys_var, "")
    except Exception:
        pass
    return ""


def get_key(key_name):
    """
    Get a key from 4 sources in priority:
      1. jarvis_keys.txt  (local file, gitignored)
      2. .env              (local env file, gitignored)
      3. Streamlit Cloud Secrets  (for cloud deployment)
      4. Windows System Environment Variables  (24/7, survives reboot)
    """
    # Priority 1: jarvis_keys.txt
    file_keys = _read_jarvis_keys_file()
    if key_name in file_keys and file_keys[key_name]:
        return file_keys[key_name]

    # Priority 2: .env file
    env_key = _load_api_key_from_env(key_name)
    if env_key:
        return env_key

    # Priority 3: Streamlit Cloud Secrets
    cloud_key = _load_api_key_from_streamlit_secrets(key_name)
    if cloud_key:
        return cloud_key

    # Priority 4: Windows System Environment Variables (24/7 mode)
    sys_key = _load_api_key_from_system(key_name)
    if sys_key:
        return sys_key

    return ""


# Backward compatibility
def load_api_key():
    """Legacy function — returns first available key from any provider."""
    for provider in ["GROQ_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY"]:
        key = get_key(provider)
        if key:
            return key
    return ""


def has_active_api_key():
    """Check if at least one API key is configured."""
    for provider in ["GROQ_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY"]:
        key = get_key(provider)
        if key and len(key) > 5:
            return True
    return False


def get_active_provider():
    """Return the first provider that has a valid key configured."""
    if get_key("GROQ_API_KEY"):
        return "groq"
    if get_key("XAI_API_KEY"):
        return "grok"
    if get_key("GEMINI_API_KEY"):
        return "gemini"
    return None


def get_provider_and_key():
    """Legacy compatibility — returns first active provider and its key."""
    provider = get_active_provider()
    if not provider:
        return None, None
    
    key_map = {
        "groq": get_key("GROQ_API_KEY"),
        "grok": get_key("XAI_API_KEY"),
        "gemini": get_key("GEMINI_API_KEY"),
    }
    return provider, key_map.get(provider, "")


# ══════════════════════════════════════════════════════════════
# PROVIDER API CALLERS
# ══════════════════════════════════════════════════════════════

def call_groq_api(prompt, key, system_instruction=None):
    """Call Groq API with llama-3.1-70b-versatile model."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.3
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"].strip()
        else:
            print(f"⚠️ Groq API Error: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        print(f"⚠️ Groq Request Exception: {str(e)}")
        return None


def call_grok_xai_api(prompt, key, system_instruction=None):
    """Call xAI/Grok API with grok-beta model."""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "grok-beta",
        "messages": messages,
        "temperature": 0.3
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"].strip()
        else:
            print(f"⚠️ xAI Grok API Error: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        print(f"⚠️ xAI Grok Request Exception: {str(e)}")
        return None


def call_gemini_api(prompt, key, system_instruction=None):
    """Call Google Gemini API with gemini-1.5-flash model."""
    import google.generativeai as genai
    
    try:
        genai.configure(api_key=key)
        full_prompt = prompt
        if system_instruction:
            full_prompt = system_instruction + "\n\n" + prompt
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(full_prompt)
        if response and response.text:
            return response.text.strip()
        else:
            print("⚠️ Gemini returned empty response")
            return None
    except Exception as e:
        print(f"⚠️ Gemini generation error: {str(e)}")
        return None


def call_best_provider(prompt, system_instruction=None):
    """
    Auto-failover: Try Groq → xAI/Grok → Gemini → None
    Returns (response_text, provider_name)
    """
    # Try Groq first
    groq_key = get_key("GROQ_API_KEY")
    if groq_key:
        res = call_groq_api(prompt, groq_key, system_instruction)
        if res:
            return res, "groq"

    # Fallback to xAI/Grok
    xai_key = get_key("XAI_API_KEY")
    if xai_key:
        res = call_grok_xai_api(prompt, xai_key, system_instruction)
        if res:
            return res, "grok"

    # Final fallback to Gemini
    gemini_key = get_key("GEMINI_API_KEY")
    if gemini_key:
        res = call_gemini_api(prompt, gemini_key, system_instruction)
        if res:
            return res, "gemini"

    return None, None


# ══════════════════════════════════════════════════════════════
# NARRATIVE GENERATORS
# ══════════════════════════════════════════════════════════════

def generate_ai_narrative(ticker, row_data):
    """
    Uses auto-failover LLM API to generate a professional, simplified investment narrative.
    Falls back to rule-based generation if no API key is available.
    """
    from report_generator import generate_stock_narrative

    provider = get_active_provider()
    if not provider:
        return generate_stock_narrative(ticker, row_data)

    prompt = f"""
    Analyze the following stock metrics and write an investment narrative in a simple, engaging, 10th-grade reading level.
    The goal is to explain why this stock is a good momentum play and any potential risks.
    
    Company Ticker: {ticker.replace('.NS', '')}
    Current Price: ₹{row_data['Price']}
    All-Time High (ATH): ₹{row_data['ATH']}
    3-Year High: ₹{row_data['3Y High']}
    Total Score on our Momentum Engine: {row_data['Total Score']}/20
    Price Score: {row_data['Price Score']}/5
    Sales Score: {row_data['Sales Score']}/5
    Profit Score: {row_data['Profit Score']}/5
    Quarter Score: {row_data['Quarter Score']}/2
    PE vs EPS Score: {row_data['PE vs EPS Score']}/3
    PE Ratio: {row_data['PE']}
    Earnings Per Share (EPS): {row_data['EPS']}
    Debt-to-Equity Ratio: {row_data['Debt/Equity']}
    Reserves: ₹{row_data['Reserves']} Crores
    Shareholding Pattern: Promoter={row_data['Promoter %']}%, Institutions={row_data['Institution %']}%, Public={row_data['Public %']}%
    Sales CAGR: {row_data.get('Sales CAGR', 0)}% (3Y: {row_data.get('Sales CAGR 3Y', 0)}%, 5Y: {row_data.get('Sales CAGR 5Y', 0)}%)
    Profit CAGR: {row_data.get('Profit CAGR', 0)}% (3Y: {row_data.get('Profit CAGR 3Y', 0)}%, 5Y: {row_data.get('Profit CAGR 5Y', 0)}%)
    Growth Accelerating (CAGR 3Y > CAGR 5Y & Overall CAGR > CAGR 3Y): {'Yes' if row_data.get('CAGR Accelerating', False) else 'No'}
    
    Instructions:
    1. Keep it under 150 words.
    2. Explain the company's financial strengths (e.g. low debt, high reserves, promoter skin in the game).
    3. Explain what a 10th grader should understand about this business's current rocket speed.
    4. Tone: Confident, insightful, and easy to read.
    """

    res, provider_name = call_best_provider(prompt)
    if res:
        return res

    return generate_stock_narrative(ticker, row_data)


def generate_ai_narrative_v2(ticker, row_data):
    """
    Uses auto-failover LLM API to generate investment narrative for Page 2 (Value & 200 SMA).
    Falls back to rule-based generation if no API key is available.
    """
    from report_generator import generate_stock_narrative_v2

    provider = get_active_provider()
    if not provider:
        return generate_stock_narrative_v2(ticker, row_data)

    price = row_data.get('Price', 0)
    sma_200 = row_data.get('200 SMA', 0)
    dist_pct = row_data.get('200 SMA Dist %', 0)
    total_score = row_data.get('Total Score', 0)
    pe = row_data.get('PE', 0)
    eps = row_data.get('EPS', 0)
    debt = row_data.get('Debt/Equity', 0)
    reserves = row_data.get('Reserves', 0)
    promoters = row_data.get('Promoter %', 0)
    inst = row_data.get('Institution %', 0)
    pub = row_data.get('Public %', 0)
    sales_cagr = row_data.get('Sales CAGR', 0)
    profit_cagr = row_data.get('Profit CAGR', 0)
    cagr_accel = row_data.get('CAGR Accelerating', False)
    value_fit = row_data.get('Value Fit', pe < eps if (pe and eps) else False)

    prompt = f"""
    Analyze the following stock metrics and write an investment narrative in a simple, engaging, 10th-grade reading level.
    The goal is to explain why this stock is a good value/momentum entry candidate and any potential risks.
    This stock passes our 200 SMA filter (meaning it trades above its 200-day simple moving average).
    
    Company Ticker: {ticker.replace('.NS', '')}
    Current Price: ₹{price}
    200-day Moving Average (200 SMA): ₹{sma_200}
    Distance from 200 SMA: {dist_pct}% (lower distance is better for entry)
    Total Score: {total_score}
    Sales CAGR: {sales_cagr}% (3Y: {row_data.get('Sales CAGR 3Y', 0)}%, 5Y: {row_data.get('Sales CAGR 5Y', 0)}%)
    Profit CAGR: {profit_cagr}% (3Y: {row_data.get('Profit CAGR 3Y', 0)}%, 5Y: {row_data.get('Profit CAGR 5Y', 0)}%)
    Growth Accelerating: {'Yes' if cagr_accel else 'No'}
    Value Fit (PE < EPS): {'Yes' if value_fit else 'No'}
    PE Ratio: {pe}
    Earnings Per Share (EPS): {eps}
    Debt-to-Equity Ratio: {debt}
    Reserves: ₹{reserves} Crores
    Shareholding Pattern: Promoter={promoters}%, Institutions={inst}%, Public={pub}%
    
    Instructions:
    1. Keep it under 150 words.
    2. Explain the company's financial strengths (e.g. low debt, high reserves, promoter holding, robust CAGR growth).
    3. Explain what a 10th grader should understand about why buying close to the 200 SMA makes sense (like buying a good product on a sensible discount near its average price).
    4. Tone: Confident, insightful, and easy to read.
    """

    res, provider_name = call_best_provider(prompt)
    if res:
        return res

    return generate_stock_narrative_v2(ticker, row_data)


def discuss_with_jarvis(user_message, chat_history, active_df, page_mode="page_1"):
    """
    Sends user message + context of top performers to auto-failover LLM API.
    Returns a response from Groq → xAI/Grok → Gemini → Error message.
    """
    provider = get_active_provider()
    if not provider:
        return "🤖 Jarvis offline. Please add API key in `jarvis_keys.txt` or set Windows System Environment Variables (JARVIS_GROQ_KEY / JARVIS_XAI_KEY / JARVIS_GEMINI_KEY)."

    try:
        # Prepare context of top picks and red alerts
        top_picks = []
        if not active_df.empty:
            cols = ["Ticker", "Price", "Total Score", "Momentum Status", "200 SMA Dist %"]
            existing_cols = [c for c in cols if c in active_df.columns]
            top_picks = active_df.head(5)[existing_cols].to_dict(orient="records")

        red_alerts = []
        if not active_df.empty:
            red_df = active_df[active_df["Red Alert"] == True]
            if not red_df.empty:
                red_alerts = red_df.head(5)[["Ticker", "Price", "Red Reasons"]].to_dict(orient="records")

        system_instructions = (
            "You are Jarvis, the advanced neural investment advisor for Bharat AI Fund Manager Gill. "
            "You are talking directly to Gurjas (Dr. Saab), the lead investor and systems CTO. "
            "Respond in a confident, direct, and slightly futuristic Hinglish (a mix of professional Hindi and English). "
            "Keep your answers concise, structured, and highly insightful. Make suggestions based on the stock scoring. "
            "Refer to yourself as Jarvis. Do not give generic advice, be bold and give concrete analysis based on our data. "
        )

        if page_mode == "page_2":
            system_instructions += (
                "We are currently examining 'Page 2: Value & 200 SMA Screener'. "
                "The stocks listed are filtered to be ABOVE their 200-day simple moving average (200 SMA), "
                "scored out of 16 points (based on annual sales/profit peaks and sales/profit CAGR growth rates), "
                "and sorted closest to their 200 SMA first (meaning low distance percentage is preferred for value/momentum entry). "
                "For PE < EPS (Value Fit), we show a star indicator instead of giving points. "
            )
        else:
            system_instructions += (
                "We are currently examining 'Page 1: Momentum & Breakout Screener'. "
                "The stocks listed are scored out of 20 points based on breakout ATH/3Y High status (5 pts), sales ATH (5 pts), "
                "profit ATH (5 pts), latest quarter performance (2 pts), and PE < EPS Value Fit (3 pts). "
            )

        system_instructions += f"\n\nActive Market Context:\nTop 5 Scored Picks: {top_picks}\nActive Blacklisted Stocks (Red Alerts): {red_alerts}\n"

        # Format conversation history
        conversation_prompt = "Conversation History:\n"
        for role, msg in chat_history[-6:]:
            conversation_prompt += f"{role}: {msg}\n"

        conversation_prompt += f"User (Gurjas): {user_message}\nJarvis:"

        # Auto-failover: try all providers
        res, used_provider = call_best_provider(conversation_prompt, system_instruction=system_instructions)
        if res:
            return res

        return (
            "🤖 Jarvis tried all available AI engines (Groq, xAI/Grok, Gemini) but none could respond. "
            "Possible issues:\n"
            "  1. API keys may be expired or out of credits\n"
            "  2. Check `jarvis_keys.txt` or System Environment Variables\n"
            "  3. Internet connection may be unstable\n\n"
            "💡 TIP: Get a free Groq key at https://console.groq.com/keys — it's the fastest!"
        )

    except Exception as e:
        return f"🤖 Jarvis Connection Error: {str(e)}. Try again or check API keys."
