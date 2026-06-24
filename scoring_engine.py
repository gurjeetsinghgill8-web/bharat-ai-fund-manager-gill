import pandas as pd
import numpy as np
from symbols import get_category

def score_stock(stock_data):
    """
    Applies the scoring rules to a single stock's data.
    Returns a dict with scores and metadata.
    """
    ticker = stock_data["ticker"]
    current_price = stock_data["current_price"]
    ath = stock_data["ath"]
    three_year_high = stock_data["three_year_high"]
    sales_hist = stock_data["sales_history"]
    profit_hist = stock_data["profit_history"]
    quarterly_profits = stock_data["quarterly_profits"]
    pe = stock_data["pe"]
    eps = stock_data["eps"]
    debt_eq = stock_data["debt_to_equity"]
    
    # 1. Price Momentum (5 Marks)
    price_score = 0
    is_at_ath = current_price >= (0.975 * ath)
    is_at_3y_high = current_price >= (0.975 * three_year_high)
    if is_at_ath or is_at_3y_high:
        price_score = 5
        
    # 2. Sales Performance (5 Marks)
    sales_score = 0
    latest_sales = sales_hist[0] if sales_hist else 0
    max_sales = max(sales_hist) if sales_hist else 0
    
    if max_sales > 0:
        if latest_sales >= (0.98 * max_sales): # ATH Sales
            sales_score = 5
        elif latest_sales >= (0.80 * max_sales): # within 10-20% drop from peak
            sales_score = 3
        else:
            sales_score = 0
            
    # 3. Profit Performance (5 Marks)
    profit_score = 0
    latest_profit = profit_hist[0] if profit_hist else 0
    max_profit = max(profit_hist) if profit_hist else 0
    
    if max_profit > 0:
        if latest_profit >= (0.98 * max_profit): # ATH Profit
            profit_score = 5
        elif latest_profit >= (0.80 * max_profit): # within 10-20% drop from peak
            profit_score = 3
        else:
            profit_score = 0

    # 4. Latest Quarter Profit (2 Marks)
    quarter_score = 0
    latest_q_profit = quarterly_profits[0] if quarterly_profits else 0
    max_q_profit = max(quarterly_profits) if quarterly_profits else 0
    if max_q_profit > 0 and latest_q_profit >= (0.98 * max_q_profit):
        quarter_score = 2
        
    # 5. PE vs EPS Score (3 Marks)
    pe_eps_score = 0
    if pe > 0 and eps > 0 and pe < eps:
        pe_eps_score = 3
        
    total_score = price_score + sales_score + profit_score + quarter_score + pe_eps_score
    
    # 6. Red Alert Check
    is_red_alert = False
    red_reasons = []
    
    if max_sales > 0 and latest_sales < (0.65 * max_sales):
        is_red_alert = True
        red_reasons.append("Sales dropped > 35% from peak")
    if max_profit > 0 and latest_profit < (0.65 * max_profit):
        is_red_alert = True
        red_reasons.append("Profit dropped > 35% from peak")
    # Normalise Debt/Equity (yfinance often returns as percentage, e.g. 10.38 for 10.38%)
    debt_decimal = debt_eq / 100.0 if debt_eq > 5.0 else debt_eq
    if debt_decimal > 2.0:
        is_red_alert = True
        red_reasons.append(f"High Debt/Equity Ratio ({round(debt_decimal, 2)})")
    if stock_data["reserves"] < 0:
        is_red_alert = True
        red_reasons.append("Negative Reserves")

    # 7. Continuous High Performance Check (1m, 2m, 6m)
    price_hist = stock_data["price_history_6m"]
    momentum_status = "Normal"
    if price_hist:
        days_30 = price_hist[-21:] if len(price_hist) >= 21 else price_hist
        days_60 = price_hist[-42:] if len(price_hist) >= 42 else price_hist
        days_180 = price_hist
        
        min_30 = min(days_30) if days_30 else 0
        max_30 = max(days_30) if days_30 else 1
        min_60 = min(days_60) if days_60 else 0
        max_60 = max(days_60) if days_60 else 1
        min_180 = min(days_180) if days_180 else 0
        max_180 = max(days_180) if days_180 else 1
        
        if min_30 >= 0.92 * max_30:
            momentum_status = "Sustained High (1 Month)"
        if min_60 >= 0.88 * max_60:
            momentum_status = "Sustained High (2 Months)"
        if min_180 >= 0.80 * max_180:
            momentum_status = "Sustained High (6 Months)"

    return {
        "Ticker": ticker,
        "Category": get_category(ticker),
        "Price": round(current_price, 2),
        "ATH": round(ath, 2),
        "3Y High": round(three_year_high, 2),
        "PE": round(pe, 2),
        "EPS": round(eps, 2),
        "Price Score": price_score,
        "Sales Score": sales_score,
        "Profit Score": profit_score,
        "Quarter Score": quarter_score,
        "PE vs EPS Score": pe_eps_score,
        "Total Score": total_score,
        "Red Alert": is_red_alert,
        "Red Reasons": ", ".join(red_reasons) if red_reasons else "None",
        "Momentum Status": momentum_status,
        "Debt/Equity": round(debt_eq, 2),
        "Reserves": round(stock_data["reserves"] / 10000000.0, 2) if stock_data["reserves"] else 0.0, # in Crores
        "Promoter %": round(stock_data["promoter_share"], 1),
        "Institution %": round(stock_data["inst_share"], 1),
        "Public %": round(stock_data["public_share"], 1)
    }

def run_scoring(batch_data):
    scored_list = []
    for ticker, data in batch_data.items():
        scored = score_stock(data)
        scored_list.append(scored)
        
    df = pd.DataFrame(scored_list)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    # Sort by total score descending
    df = df.sort_values(by="Total Score", ascending=False)
    
    # Latest Highs (Price Score = 5)
    latest_highs_df = df[df["Price Score"] == 5].copy()
    
    # Continuous Performers (Momentum Status != Normal)
    continuous_performers_df = df[df["Momentum Status"] != "Normal"].copy()
    
    # Red Alerts
    red_alerts_df = df[df["Red Alert"] == True].copy()
    
    return df, latest_highs_df, continuous_performers_df, red_alerts_df
