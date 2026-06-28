import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def load_api_key():
    """
    Tries to read the Gemini API key from api_key.txt first, then falls back to .env
    """
    key_path = "api_key.txt"
    if os.path.exists(key_path):
        try:
            with open(key_path, "r") as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and len(line) > 10:
                        return line
        except Exception:
            pass
            
    # Fallback to env
    return os.getenv("GEMINI_API_KEY")

def has_active_api_key():
    key = load_api_key()
    return key is not None and len(key) > 5

# Initialize client if key exists
api_key = load_api_key()
if api_key:
    genai.configure(api_key=api_key)

def generate_ai_narrative(ticker, row_data):
    """
    Uses Gemini LLM to generate a professional, simplified 10th-grade level investment narrative.
    Falls back to rule-based generation if API key is not present.
    """
    from report_generator import generate_stock_narrative # local import to prevent circularity
    
    if not has_active_api_key():
        # Fallback to local rule-based builder
        return generate_stock_narrative(ticker, row_data)
        
    try:
        # Re-configure to ensure fresh load
        genai.configure(api_key=load_api_key())
        model = genai.GenerativeModel('gemini-1.5-flash')
        
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
        
        Instructions:
        1. Keep it under 150 words.
        2. Explain the company's financial strengths (e.g. low debt, high reserves, promoter skin in the game).
        3. Explain what a 10th grader should understand about this business's current rocket speed.
        4. Tone: Confident, insightful, and easy to read.
        """
        
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
        else:
            return generate_stock_narrative(ticker, row_data)
            
    except Exception as e:
        print(f"Gemini generation error: {str(e)}. Falling back to local template.")
        return generate_stock_narrative(ticker, row_data)

def generate_ai_narrative_v2(ticker, row_data):
    """
    Uses Gemini LLM to generate a professional, simplified 10th-grade level investment narrative for Page 2 (Value & 200 SMA).
    Falls back to rule-based generation if API key is not present.
    """
    from report_generator import generate_stock_narrative_v2 # local import to prevent circularity
    
    if not has_active_api_key():
        # Fallback to local rule-based builder
        return generate_stock_narrative_v2(ticker, row_data)
        
    try:
        # Re-configure to ensure fresh load
        genai.configure(api_key=load_api_key())
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Analyze the following stock metrics and write an investment narrative in a simple, engaging, 10th-grade reading level.
        The goal is to explain why this stock is a good value/momentum entry candidate and any potential risks.
        This stock passes our 200 SMA filter (meaning it trades above its 200-day simple moving average).
        
        Company Ticker: {ticker.replace('.NS', '')}
        Current Price: ₹{row_data['Price']}
        200-day Moving Average (200 SMA): ₹{row_data['200 SMA']}
        Distance from 200 SMA: {row_data['200 SMA Dist %']}% (lower distance is better for entry)
        Total Score on our Value/SMA Engine: {row_data['Total Score']}/16
        Sales Score: {row_data['Sales Score']}/5
        Profit Score: {row_data['Profit Score']}/5
        Sales CAGR (Compounded Annual growth rate): {row_data['Sales CAGR']}% (Score: {row_data['Sales CAGR Score']}/3)
        Profit CAGR (Compounded Annual growth rate): {row_data['Profit CAGR']}% (Score: {row_data['Profit CAGR Score']}/3)
        Value Fit (PE < EPS): {'Yes' if row_data['Value Fit'] else 'No'}
        PE Ratio: {row_data['PE']}
        Earnings Per Share (EPS): {row_data['EPS']}
        Debt-to-Equity Ratio: {row_data['Debt/Equity']}
        Reserves: ₹{row_data['Reserves']} Crores
        Shareholding Pattern: Promoter={row_data['Promoter %']}%, Institutions={row_data['Institution %']}%, Public={row_data['Public %']}%
        
        Instructions:
        1. Keep it under 150 words.
        2. Explain the company's financial strengths (e.g. low debt, high reserves, promoter holding, robust CAGR growth).
        3. Explain what a 10th grader should understand about why buying close to the 200 SMA makes sense (like buying a good product on a sensible discount near its average price).
        4. Tone: Confident, insightful, and easy to read.
        """
        
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
        else:
            return generate_stock_narrative_v2(ticker, row_data)
            
    except Exception as e:
        print(f"Gemini generation error: {str(e)}. Falling back to local template.")
        return generate_stock_narrative_v2(ticker, row_data)

def discuss_with_jarvis(user_message, chat_history, active_df, page_mode="page_1"):
    """
    Sends the user message, context of top performers, and chat history to Gemini.
    """
    if not has_active_api_key():
        return "Jarvis offline. Gemini API key is missing in `api_key.txt` or `.env`. Please add your free key to enable conversations!"
        
    try:
        genai.configure(api_key=load_api_key())
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare context of top picks and red alerts
        top_picks = []
        if not active_df.empty:
            cols = ["Ticker", "Price", "Total Score", "Momentum Status", "200 SMA Dist %"]
            existing_cols = [c for c in cols if c in active_df.columns]
            top_picks = active_df.head(5)[existing_cols].to_dict(orient="records")
            
        red_alerts = []
        if not active_df.empty:
            red_alerts = active_df[active_df["Red Alert"] == True].head(5)[["Ticker", "Price", "Red Reasons"]].to_dict(orient="records")
            
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
        
        # Format conversation history for prompt
        conversation_prompt = system_instructions + "\nConversation History:\n"
        for role, msg in chat_history[-6:]: # Keep last 6 messages
            conversation_prompt += f"{role}: {msg}\n"
            
        conversation_prompt += f"User (Gurjas): {user_message}\nJarvis:"
        
        response = model.generate_content(conversation_prompt)
        if response and response.text:
            return response.text.strip()
        return "Jarvis is compiling data... Please repeat that."
        
    except Exception as e:
        return f"Jarvis Connection Error: {str(e)}. Please check your API key validity."
