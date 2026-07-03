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

    # 8. CAGR Acceleration Check (Growth Momentum)
    sales_cagr_5y = calculate_cagr_for_years(sales_hist, 4)
    sales_cagr_3y = calculate_cagr_for_years(sales_hist, 2)
    sales_cagr_all = calculate_cagr(sales_hist)
    profit_cagr_5y = calculate_cagr_for_years(profit_hist, 4)
    profit_cagr_3y = calculate_cagr_for_years(profit_hist, 2)
    profit_cagr_all = calculate_cagr(profit_hist)

    # Condition: Sales growth 3Years > Sales growth 5Years AND Sales growth > Sales growth 3Years
    sales_growth_accelerating = False
    if (sales_cagr_3y is not None and sales_cagr_5y is not None and sales_cagr_all is not None
            and sales_cagr_3y > sales_cagr_5y and sales_cagr_all > sales_cagr_3y):
        sales_growth_accelerating = True

    # Condition: Profit growth > 10 AND Profit growth 3Years > Profit growth 5Years AND Profit growth > Profit growth 3Years
    profit_growth_accelerating = False
    if (profit_cagr_all is not None and profit_cagr_3y is not None and profit_cagr_5y is not None
            and profit_cagr_all > 10.0 and profit_cagr_3y > profit_cagr_5y and profit_cagr_all > profit_cagr_3y):
        profit_growth_accelerating = True

    # Overall CAGR Accelerating Flag
    cagr_accelerating = sales_growth_accelerating and profit_growth_accelerating

    # --- 200 SMA Fields (from stock_data cache) ---
    sma_200 = stock_data.get("sma_200", 0.0)
    is_above_200_sma = True
    dist_pct = 0.0
    if sma_200 > 0:
        is_above_200_sma = current_price >= sma_200
        dist_pct = ((current_price - sma_200) / sma_200) * 100.0

    # --- Star Rating (1-3 stars based on CAGR quality + score) ---
    star_rating = 0
    if cagr_accelerating and total_score >= 14:
        star_rating = 3  # ⭐⭐⭐ Best quality
    elif (sales_growth_accelerating or profit_growth_accelerating) and total_score >= 10:
        star_rating = 2  # ⭐⭐ Good quality
    elif total_score >= 8:
        star_rating = 1  # ⭐ Decent

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
        "Star Rating": star_rating,
        "Red Alert": is_red_alert,
        "Red Reasons": ", ".join(red_reasons) if red_reasons else "None",
        "Momentum Status": momentum_status,
        "Debt/Equity": round(debt_eq, 2),
        "Reserves": round(stock_data["reserves"] / 10000000.0, 2) if stock_data["reserves"] else 0.0, # in Crores
        "Promoter %": round(stock_data["promoter_share"], 1),
        "Institution %": round(stock_data["inst_share"], 1),
        "Public %": round(stock_data["public_share"], 1),
        "Sales CAGR": round(sales_cagr_all, 2) if sales_cagr_all is not None else 0.0,
        "Sales CAGR 3Y": round(sales_cagr_3y, 2) if sales_cagr_3y is not None else 0.0,
        "Sales CAGR 5Y": round(sales_cagr_5y, 2) if sales_cagr_5y is not None else 0.0,
        "Profit CAGR": round(profit_cagr_all, 2) if profit_cagr_all is not None else 0.0,
        "Profit CAGR 3Y": round(profit_cagr_3y, 2) if profit_cagr_3y is not None else 0.0,
        "Profit CAGR 5Y": round(profit_cagr_5y, 2) if profit_cagr_5y is not None else 0.0,
        "Sales Growth Accelerating": sales_growth_accelerating,
        "Profit Growth Accelerating": profit_growth_accelerating,
        "CAGR Accelerating": cagr_accelerating,
        "200 SMA": round(sma_200, 2) if sma_200 else 0.0,
        "200 SMA Dist %": round(dist_pct, 2) if sma_200 else 0.0,
        "Is Above 200 SMA": is_above_200_sma
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

def calculate_cagr(history):
    """
    Calculates Compounded Annual Growth Rate (CAGR) from history list.
    index 0 is the latest year, index -1 is the oldest year.
    """
    if not history or len(history) < 2:
        return 0.0
    latest = history[0]
    oldest = history[-1]
    if oldest <= 0 or latest <= 0:
        return 0.0
    n = len(history) - 1
    try:
        return ((latest / oldest) ** (1 / n) - 1) * 100.0
    except Exception:
        return 0.0

def calculate_cagr_for_years(history, years):
    """
    Calculates CAGR over the last N years from the history list.
    history[0] = latest year, history[-1] = oldest year.
    Returns the CAGR percentage.
    """
    if not history or len(history) < years + 1:
        return None
    latest = history[0]
    oldest = history[years]  # years ago
    if oldest <= 0 or latest <= 0:
        return None
    try:
        return ((latest / oldest) ** (1 / years) - 1) * 100.0
    except Exception:
        return None

def score_stock_v2(stock_data):
    """
    Applies the Page 2 scoring rules to a single stock's data.
    Returns a dict with scores and metadata.
    """
    ticker = stock_data["ticker"]
    current_price = stock_data["current_price"]
    ath = stock_data["ath"]
    three_year_high = stock_data["three_year_high"]
    sales_hist = stock_data["sales_history"]
    profit_hist = stock_data["profit_history"]
    pe = stock_data["pe"]
    eps = stock_data["eps"]
    debt_eq = stock_data["debt_to_equity"]
    sma_200 = stock_data.get("sma_200", 0.0)
    
    # Proximity and filter check for 200 SMA
    is_above_200_sma = True
    dist_pct = 0.0
    if sma_200 > 0:
        is_above_200_sma = current_price >= sma_200
        dist_pct = ((current_price - sma_200) / sma_200) * 100.0
    else:
        # If no sma_200 is available, we assume it passes but flag it
        is_above_200_sma = True
        dist_pct = 0.0
        
    # 1. Sales Performance (5 Marks)
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
            
    # 2. Profit Performance (5 Marks)
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

    # 3. Annual Sales CAGR (3 Marks)
    sales_cagr = calculate_cagr(sales_hist)
    sales_cagr_score = 0
    if sales_cagr > 20.0:
        sales_cagr_score = 3
    elif sales_cagr > 15.0:
        sales_cagr_score = 2
    elif sales_cagr > 10.0:
        sales_cagr_score = 1
        
    # 4. Annual Profit CAGR (3 Marks)
    profit_cagr = calculate_cagr(profit_hist)
    profit_cagr_score = 0
    if profit_cagr > 20.0:
        profit_cagr_score = 3
    elif profit_cagr > 15.0:
        profit_cagr_score = 2
    elif profit_cagr > 10.0:
        profit_cagr_score = 1
        
    # 5. Value / Momentum Fit (PE < EPS) - No Points, just indicator (tick mark/star)
    value_fit = False
    if pe > 0 and eps > 0 and pe < eps:
        value_fit = True
        
    total_score = sales_score + profit_score + sales_cagr_score + profit_cagr_score
    
    # 6. Red Alert Check (Keep same as original)
    is_red_alert = False
    red_reasons = []
    
    if max_sales > 0 and latest_sales < (0.65 * max_sales):
        is_red_alert = True
        red_reasons.append("Sales dropped > 35% from peak")
    if max_profit > 0 and latest_profit < (0.65 * max_profit):
        is_red_alert = True
        red_reasons.append("Profit dropped > 35% from peak")
    
    debt_decimal = debt_eq / 100.0 if debt_eq > 5.0 else debt_eq
    if debt_decimal > 2.0:
        is_red_alert = True
        red_reasons.append(f"High Debt/Equity Ratio ({round(debt_decimal, 2)})")
    if stock_data["reserves"] < 0:
        is_red_alert = True
        red_reasons.append("Negative Reserves")

    # 7. Momentum status (Keep same as original)
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
        elif min_60 >= 0.88 * max_60:
            momentum_status = "Sustained High (2 Months)"
        elif min_180 >= 0.80 * max_180:
            momentum_status = "Sustained High (6 Months)"

    # 8. CAGR Acceleration Check (Growth Momentum)
    sales_cagr_5y = calculate_cagr_for_years(sales_hist, 4)
    sales_cagr_3y = calculate_cagr_for_years(sales_hist, 2)
    sales_cagr_all = sales_cagr  # Already computed above
    profit_cagr_5y = calculate_cagr_for_years(profit_hist, 4)
    profit_cagr_3y = calculate_cagr_for_years(profit_hist, 2)
    profit_cagr_all = profit_cagr  # Already computed above

    # Condition: Sales growth 3Years > Sales growth 5Years AND Sales growth > Sales growth 3Years
    sales_growth_accelerating = False
    if (sales_cagr_3y is not None and sales_cagr_5y is not None and sales_cagr_all is not None
            and sales_cagr_3y > sales_cagr_5y and sales_cagr_all > sales_cagr_3y):
        sales_growth_accelerating = True

    # Condition: Profit growth > 10 AND Profit growth 3Years > Profit growth 5Years AND Profit growth > Profit growth 3Years
    profit_growth_accelerating = False
    if (profit_cagr_all is not None and profit_cagr_3y is not None and profit_cagr_5y is not None
            and profit_cagr_all > 10.0 and profit_cagr_3y > profit_cagr_5y and profit_cagr_all > profit_cagr_3y):
        profit_growth_accelerating = True

    # Overall CAGR Accelerating Flag
    cagr_accelerating = sales_growth_accelerating and profit_growth_accelerating

    # --- Star Rating (1-3 stars based on CAGR quality + score) ---
    star_rating = 0
    if cagr_accelerating and total_score >= 11:
        star_rating = 3  # ⭐⭐⭐ Best quality
    elif (sales_growth_accelerating or profit_growth_accelerating) and total_score >= 8:
        star_rating = 2  # ⭐⭐ Good quality
    elif total_score >= 6:
        star_rating = 1  # ⭐ Decent

    return {
        "Ticker": ticker,
        "Category": get_category(ticker),
        "Price": round(current_price, 2),
        "ATH": round(ath, 2),
        "3Y High": round(three_year_high, 2),
        "PE": round(pe, 2),
        "EPS": round(eps, 2),
        "Sales Score": sales_score,
        "Profit Score": profit_score,
        "Sales CAGR": round(sales_cagr, 2) if sales_cagr else 0.0,
        "Sales CAGR 3Y": round(sales_cagr_3y, 2) if sales_cagr_3y is not None else 0.0,
        "Sales CAGR 5Y": round(sales_cagr_5y, 2) if sales_cagr_5y is not None else 0.0,
        "Sales CAGR Score": sales_cagr_score,
        "Profit CAGR": round(profit_cagr, 2) if profit_cagr else 0.0,
        "Profit CAGR 3Y": round(profit_cagr_3y, 2) if profit_cagr_3y is not None else 0.0,
        "Profit CAGR 5Y": round(profit_cagr_5y, 2) if profit_cagr_5y is not None else 0.0,
        "Profit CAGR Score": profit_cagr_score,
        "Sales Growth Accelerating": sales_growth_accelerating,
        "Profit Growth Accelerating": profit_growth_accelerating,
        "CAGR Accelerating": cagr_accelerating,
        "Value Fit": value_fit,
        "Star Rating": star_rating,
        "Total Score": total_score,
        "Red Alert": is_red_alert,
        "Red Reasons": ", ".join(red_reasons) if red_reasons else "None",
        "Momentum Status": momentum_status,
        "Debt/Equity": round(debt_eq, 2),
        "Reserves": round(stock_data["reserves"] / 10000000.0, 2) if stock_data["reserves"] else 0.0, # in Crores
        "Promoter %": round(stock_data["promoter_share"], 1),
        "Institution %": round(stock_data["inst_share"], 1),
        "Public %": round(stock_data["public_share"], 1),
        "200 SMA": round(sma_200, 2) if sma_200 else 0.0,
        "200 SMA Dist %": round(dist_pct, 2) if sma_200 else 0.0,
        "Is Above 200 SMA": is_above_200_sma
    }

def run_scoring_v2(batch_data):
    scored_list = []
    for ticker, data in batch_data.items():
        scored = score_stock_v2(data)
        # Filter: If SMA details are present, filter out stocks where Is Above 200 SMA is False
        if scored["200 SMA"] > 0 and not scored["Is Above 200 SMA"]:
            continue
        scored_list.append(scored)
        
    df = pd.DataFrame(scored_list)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    # Sort by 200 SMA Dist % ascending by default
    df = df.sort_values(by="200 SMA Dist %", ascending=True)
    
    # Continuous Performers (Momentum Status != Normal)
    continuous_performers_df = df[df["Momentum Status"] != "Normal"].copy()
    
    # Red Alerts
    red_alerts_df = df[df["Red Alert"] == True].copy()
    
    return df, continuous_performers_df, red_alerts_df
