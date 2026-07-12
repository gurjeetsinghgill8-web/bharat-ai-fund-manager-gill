import pandas as pd
import numpy as np
from symbols import get_category


# ══════════════════════════════════════════════════════════════
# CAGR STAR RATING SYSTEM (Gurdeep's 24-Star System)
# ══════════════════════════════════════════════════════════════
# Each CAGR value gets stars based on threshold:
#   ≥ 10% → 1 star
#   ≥ 15% → 2 stars
#   ≥ 20% → 3 stars
#   ≥ 25% → 4 stars
#
# Sales side (Overall + 3Y + 5Y) = max 12 stars
# Profit side (Overall + 3Y + 5Y) = max 12 stars
# Total = max 24 stars
# ══════════════════════════════════════════════════════════════

def _cagr_to_stars(cagr_value):
    """Convert a single CAGR percentage to star count (0-4)."""
    if cagr_value is None or cagr_value <= 0:
        return 0
    if cagr_value >= 25.0:
        return 4
    if cagr_value >= 20.0:
        return 3
    if cagr_value >= 15.0:
        return 2
    if cagr_value >= 10.0:
        return 1
    return 0


def _cagr_stars_display(cagr_value):
    """Returns (star_count, display_string) like (3, '20.5') or (0, '0')."""
    stars = _cagr_to_stars(cagr_value)
    val_str = f"{cagr_value:.1f}" if cagr_value and cagr_value > 0 else "0"
    return stars, val_str


def _make_star_bar(star_count, max_stars=4):
    """Create visual star string like ⭐⭐⭐ (3 stars)."""
    return "⭐" * star_count + "☆" * (max_stars - star_count)


def compute_cagr_stars(sales_cagr_all, sales_cagr_3y, sales_cagr_5y,
                        profit_cagr_all, profit_cagr_3y, profit_cagr_5y):
    """
    Compute the full Gurdeep 24-Star Rating.
    Returns dict with all star info.
    """
    # Sales side stars
    s_all_stars, s_all_val = _cagr_stars_display(sales_cagr_all)
    s_3y_stars, s_3y_val = _cagr_stars_display(sales_cagr_3y)
    s_5y_stars, s_5y_val = _cagr_stars_display(sales_cagr_5y)
    
    # Profit side stars
    p_all_stars, p_all_val = _cagr_stars_display(profit_cagr_all)
    p_3y_stars, p_3y_val = _cagr_stars_display(profit_cagr_3y)
    p_5y_stars, p_5y_val = _cagr_stars_display(profit_cagr_5y)
    
    # Totals
    sales_total_stars = s_all_stars + s_3y_stars + s_5y_stars
    profit_total_stars = p_all_stars + p_3y_stars + p_5y_stars
    grand_total_stars = sales_total_stars + profit_total_stars
    
    return {
        # Sales individual
        "Sales CAGR Stars": s_all_stars,
        "Sales CAGR 3Y Stars": s_3y_stars,
        "Sales CAGR 5Y Stars": s_5y_stars,
        "Sales CAGR Star Bar": f"{_make_star_bar(s_all_stars)} {s_all_val}",
        "Sales CAGR 3Y Star Bar": f"{_make_star_bar(s_3y_stars)} {s_3y_val}",
        "Sales CAGR 5Y Star Bar": f"{_make_star_bar(s_5y_stars)} {s_5y_val}",
        # Profit individual
        "Profit CAGR Stars": p_all_stars,
        "Profit CAGR 3Y Stars": p_3y_stars,
        "Profit CAGR 5Y Stars": p_5y_stars,
        "Profit CAGR Star Bar": f"{_make_star_bar(p_all_stars)} {p_all_val}",
        "Profit CAGR 3Y Star Bar": f"{_make_star_bar(p_3y_stars)} {p_3y_val}",
        "Profit CAGR 5Y Star Bar": f"{_make_star_bar(p_5y_stars)} {p_5y_val}",
        # Totals
        "Sales Star Total": sales_total_stars,  # /12
        "Profit Star Total": profit_total_stars,  # /12
        "Total Star Rating": grand_total_stars,  # /24
        "Star Badge": f"{'⭐' * min(grand_total_stars, 24)} ({grand_total_stars}/24)"
        if grand_total_stars > 0 else "No Stars",
    }


def _detect_turnaround(sales_cagr_all, sales_cagr_3y, sales_cagr_5y,
                        profit_cagr_all, profit_cagr_3y, profit_cagr_5y):
    """
    Detect "Turn Around" situation:
    - Overall CAGR > BOTH 3Y and 5Y CAGRs AND Overall CAGR > 10
    - This means recent years were weak but older good data pulls overall up
    Returns (is_turnaround: bool, description: str)
    """
    reasons = []
    # Sales turnaround check
    sales_turn = False
    if (sales_cagr_all is not None and sales_cagr_3y is not None and sales_cagr_5y is not None
            and sales_cagr_all > 10.0
            and sales_cagr_all > sales_cagr_3y and sales_cagr_all > sales_cagr_5y):
        sales_turn = True
        reasons.append(f"Sales TA({sales_cagr_all:.1f}% > 3Y:{sales_cagr_3y:.1f}% & 5Y:{sales_cagr_5y:.1f}%)")
    
    # Profit turnaround check
    profit_turn = False
    if (profit_cagr_all is not None and profit_cagr_3y is not None and profit_cagr_5y is not None
            and profit_cagr_all > 10.0
            and profit_cagr_all > profit_cagr_3y and profit_cagr_all > profit_cagr_5y):
        profit_turn = True
        reasons.append(f"Profit TA({profit_cagr_all:.1f}% > 3Y:{profit_cagr_3y:.1f}% & 5Y:{profit_cagr_5y:.1f}%)")
    
    is_turnaround = sales_turn or profit_turn
    desc = "; ".join(reasons) if reasons else ""
    return is_turnaround, desc


def _compute_turnaround_bonus_stars(turnaround_data, star_data):
    """
    If a stock is a Turn Around AND overall CAGR > 15, add +1 bonus star
    to the grand total (capped at 24).
    """
    is_turnaround = turnaround_data[0]
    if not is_turnaround:
        return star_data["Total Star Rating"], star_data["Star Badge"]
    
    bonus = 1  # +1 star for turnaround story
    new_total = min(star_data["Total Star Rating"] + bonus, 24)
    new_badge = f"{'⭐' * new_total} ({new_total}/24) 🔄 TA" if new_total > 0 else "No Stars 🔄 TA"
    return new_total, new_badge


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
    
    # 1. Price Momentum (5 Marks) - Excluded from Total Score per Gurjas's simplified logic
    price_score = 0
        
    # 2. Sales Performance (5 Marks)
    sales_score = 0
    latest_sales = sales_hist[0] if sales_hist else 0
    max_sales = max(sales_hist) if sales_hist else 0
    
    if max_sales > 0 and latest_sales >= (0.98 * max_sales): # ATH Sales
        sales_score = 5
            
    # 3. Profit Performance (5 Marks)
    profit_score = 0
    latest_profit = profit_hist[0] if profit_hist else 0
    max_profit = max(profit_hist) if profit_hist else 0
    
    if max_profit > 0 and latest_profit >= (0.98 * max_profit): # ATH Profit
        profit_score = 5
 
    # 4. Latest Quarter Profit (2 Marks) - Excluded
    quarter_score = 0
        
    # 5. PE vs EPS Score (3 Marks) - Excluded
    pe_eps_score = 0
        
    total_score = sales_score + profit_score
    
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

    # ── UPGRADED CRITERIA (Gurdeep's Sensible Logic) ──
    # Sales growth 3Years > 10 AND Sales growth > Sales growth 3Years AND Sales growth 5Years > 10
    sales_growth_accelerating = False
    if (sales_cagr_3y is not None and sales_cagr_all is not None and sales_cagr_5y is not None
            and sales_cagr_3y > 10.0 and sales_cagr_all > sales_cagr_3y and sales_cagr_5y > 10.0):
        sales_growth_accelerating = True

    # Profit growth > 10 AND Profit growth 3Years > 10 AND Profit growth > Profit growth 3Years
    # AND Profit growth 3Years > Profit growth 5Years
    profit_growth_accelerating = False
    if (profit_cagr_all is not None and profit_cagr_3y is not None and profit_cagr_5y is not None
            and profit_cagr_all > 10.0 and profit_cagr_3y > 10.0
            and profit_cagr_all > profit_cagr_3y and profit_cagr_3y > profit_cagr_5y):
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

    # Sector / Industry / Exchange
    sector = stock_data.get("sector", "Unknown")
    industry = stock_data.get("industry", "Unknown")
    exchange = stock_data.get("exchange", "NSE")

    # === GURDEEP'S 24-STAR RATING SYSTEM (CAGR Thresholds) ===
    # Sales stars: Overall + 3Y + 5Y = max 12
    # Profit stars: Overall + 3Y + 5Y = max 12
    # Grand total = max 24
    star_data = compute_cagr_stars(
        sales_cagr_all, sales_cagr_3y, sales_cagr_5y,
        profit_cagr_all, profit_cagr_3y, profit_cagr_5y
    )

    # === TURN AROUND DETECTION ===
    turnaround_data = _detect_turnaround(
        sales_cagr_all, sales_cagr_3y, sales_cagr_5y,
        profit_cagr_all, profit_cagr_3y, profit_cagr_5y
    )
    is_turnaround, turnaround_desc = turnaround_data

    # Bonus star for turnaround stories
    total_star_rating, star_badge = _compute_turnaround_bonus_stars(turnaround_data, star_data)

    # Sales+Profit CAGR Total (quick sum metric)
    sales_profit_cagr_total = (sales_cagr_all if sales_cagr_all else 0) + (profit_cagr_all if profit_cagr_all else 0)

    return {
        "Ticker": ticker,
        "Category": get_category(ticker),
        "Sector": sector,
        "Industry": industry,
        "Exchange": exchange,
        "Price": round(current_price, 2),
        "200 SMA": round(sma_200, 2) if sma_200 else 0.0,
        "200 SMA Dist %": round(dist_pct, 2) if sma_200 else 0.0,
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
        # --- OLD STAR RATING (legacy, kept for backward compat) ---
        "Star Rating": star_data["Total Star Rating"],
        # --- NEW 24-STAR SYSTEM ---
        "Sales CAGR Stars": star_data["Sales CAGR Stars"],
        "Sales CAGR 3Y Stars": star_data["Sales CAGR 3Y Stars"],
        "Sales CAGR 5Y Stars": star_data["Sales CAGR 5Y Stars"],
        "Sales CAGR Star Bar": star_data["Sales CAGR Star Bar"],
        "Sales CAGR 3Y Star Bar": star_data["Sales CAGR 3Y Star Bar"],
        "Sales CAGR 5Y Star Bar": star_data["Sales CAGR 5Y Star Bar"],
        "Profit CAGR Stars": star_data["Profit CAGR Stars"],
        "Profit CAGR 3Y Stars": star_data["Profit CAGR 3Y Stars"],
        "Profit CAGR 5Y Stars": star_data["Profit CAGR 5Y Stars"],
        "Profit CAGR Star Bar": star_data["Profit CAGR Star Bar"],
        "Profit CAGR 3Y Star Bar": star_data["Profit CAGR 3Y Star Bar"],
        "Profit CAGR 5Y Star Bar": star_data["Profit CAGR 5Y Star Bar"],
        "Sales Star Total": star_data["Sales Star Total"],   # /12
        "Profit Star Total": star_data["Profit Star Total"], # /12
        "Total Star Rating": total_star_rating, # with bonus TA stars
        "Star Badge": star_badge,  # with 🔄 TA badge
        "Stars (Sales Total)": f"{star_data['Sales Star Total']}/12",
        "Stars (Profit Total)": f"{star_data['Profit Star Total']}/12",
        "Stars (Total)": f"{total_star_rating}/24",
        "Sales+Profit CAGR Total": round(sales_profit_cagr_total, 2),
        "Turn Around": is_turnaround,
        "Turn Around Desc": turnaround_desc,
        # --- RED ALERT ---
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
        "Is Above 200 SMA": is_above_200_sma,
        # --- BULL STATUS ---
        "Bull Status": "🐂🐂 Double Bull" if ((sales_cagr_all is not None and sales_cagr_all > 20.0) and (profit_cagr_all is not None and profit_cagr_all > 20.0) and (sales_score == 5 and profit_score == 5)) else (
            "🐂 Bull" if (((sales_cagr_all is not None and sales_cagr_all > 20.0) and (profit_cagr_all is not None and profit_cagr_all > 20.0)) or (sales_score == 5 and profit_score == 5)) else ""
        )
    }

def run_scoring(batch_data):
    scored_list = []
    for ticker, data in batch_data.items():
        scored = score_stock(data)
        scored_list.append(scored)
        
    df = pd.DataFrame(scored_list)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    # Priority: Sort by Star Rating descending (5★ first), then Total Score descending
    df = df.sort_values(by=["Star Rating", "Total Score"], ascending=[False, False])
    
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
    
    # Sector / Industry / Exchange
    sector = stock_data.get("sector", "Unknown")
    industry = stock_data.get("industry", "Unknown")
    exchange = stock_data.get("exchange", "NSE")
    
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

    # ── UPGRADED CRITERIA (Gurdeep's Sensible Logic) ──
    # Sales growth 3Years > 10 AND Sales growth > Sales growth 3Years AND Sales growth 5Years > 10
    sales_growth_accelerating = False
    if (sales_cagr_3y is not None and sales_cagr_all is not None and sales_cagr_5y is not None
            and sales_cagr_3y > 10.0 and sales_cagr_all > sales_cagr_3y and sales_cagr_5y > 10.0):
        sales_growth_accelerating = True

    # Profit growth > 10 AND Profit growth 3Years > 10 AND Profit growth > Profit growth 3Years
    # AND Profit growth 3Years > Profit growth 5Years
    profit_growth_accelerating = False
    if (profit_cagr_all is not None and profit_cagr_3y is not None and profit_cagr_5y is not None
            and profit_cagr_all > 10.0 and profit_cagr_3y > 10.0
            and profit_cagr_all > profit_cagr_3y and profit_cagr_3y > profit_cagr_5y):
        profit_growth_accelerating = True

    # Overall CAGR Accelerating Flag
    cagr_accelerating = sales_growth_accelerating and profit_growth_accelerating

    # === GURDEEP'S 24-STAR RATING SYSTEM (CAGR Thresholds) ===
    star_data = compute_cagr_stars(
        sales_cagr_all, sales_cagr_3y, sales_cagr_5y,
        profit_cagr_all, profit_cagr_3y, profit_cagr_5y
    )

    # === TURN AROUND DETECTION ===
    turnaround_data = _detect_turnaround(
        sales_cagr_all, sales_cagr_3y, sales_cagr_5y,
        profit_cagr_all, profit_cagr_3y, profit_cagr_5y
    )
    is_turnaround, turnaround_desc = turnaround_data

    # Bonus star for turnaround stories
    total_star_rating, star_badge = _compute_turnaround_bonus_stars(turnaround_data, star_data)

    # Sales+Profit CAGR Total (quick sum metric)
    sales_profit_cagr_total = (sales_cagr_all if sales_cagr_all else 0) + (profit_cagr_all if profit_cagr_all else 0)

    return {
        "Ticker": ticker,
        "Exchange": exchange,
        "Sector": sector,
        "Industry": industry,
        "Category": get_category(ticker),
        "Price": round(current_price, 2),
        "200 SMA": round(sma_200, 2) if sma_200 else 0.0,
        "200 SMA Dist %": round(dist_pct, 2) if sma_200 else 0.0,
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
        # --- NEW 24-STAR SYSTEM ---
        "Sales CAGR Stars": star_data["Sales CAGR Stars"],
        "Sales CAGR 3Y Stars": star_data["Sales CAGR 3Y Stars"],
        "Sales CAGR 5Y Stars": star_data["Sales CAGR 5Y Stars"],
        "Sales CAGR Star Bar": star_data["Sales CAGR Star Bar"],
        "Sales CAGR 3Y Star Bar": star_data["Sales CAGR 3Y Star Bar"],
        "Sales CAGR 5Y Star Bar": star_data["Sales CAGR 5Y Star Bar"],
        "Profit CAGR Stars": star_data["Profit CAGR Stars"],
        "Profit CAGR 3Y Stars": star_data["Profit CAGR 3Y Stars"],
        "Profit CAGR 5Y Stars": star_data["Profit CAGR 5Y Stars"],
        "Profit CAGR Star Bar": star_data["Profit CAGR Star Bar"],
        "Profit CAGR 3Y Star Bar": star_data["Profit CAGR 3Y Star Bar"],
        "Profit CAGR 5Y Star Bar": star_data["Profit CAGR 5Y Star Bar"],
        "Sales Star Total": star_data["Sales Star Total"],   # /12
        "Profit Star Total": star_data["Profit Star Total"], # /12
        "Total Star Rating": total_star_rating, # with bonus TA stars
        "Star Badge": star_badge,  # with 🔄 TA badge
        "Stars (Sales Total)": f"{star_data['Sales Star Total']}/12",
        "Stars (Profit Total)": f"{star_data['Profit Star Total']}/12",
        "Stars (Total)": f"{total_star_rating}/24",
        "Sales+Profit CAGR Total": round(sales_profit_cagr_total, 2),
        "Turn Around": is_turnaround,
        "Turn Around Desc": turnaround_desc,
        # --- CAGR ACCELERATION ---
        "Sales Growth Accelerating": sales_growth_accelerating,
        "Profit Growth Accelerating": profit_growth_accelerating,
        "CAGR Accelerating": cagr_accelerating,
        "Value Fit": value_fit,
        "Star Rating": total_star_rating,
        "Total Score": total_score,
        "Red Alert": is_red_alert,
        "Red Reasons": ", ".join(red_reasons) if red_reasons else "None",
        "Momentum Status": momentum_status,
        "Debt/Equity": round(debt_eq, 2),
        "Reserves": round(stock_data["reserves"] / 10000000.0, 2) if stock_data["reserves"] else 0.0, # in Crores
        "Promoter %": round(stock_data["promoter_share"], 1),
        "Institution %": round(stock_data["inst_share"], 1),
        "Public %": round(stock_data["public_share"], 1),
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
        
    # Priority: Sort by Star Rating descending (5★ first), then nearest to 200 SMA
    df = df.sort_values(by=["Star Rating", "200 SMA Dist %"], ascending=[False, True])
    
    # Continuous Performers (Momentum Status != Normal)
    continuous_performers_df = df[df["Momentum Status"] != "Normal"].copy()
    
    # Red Alerts
    red_alerts_df = df[df["Red Alert"] == True].copy()
    
    return df, continuous_performers_df, red_alerts_df
