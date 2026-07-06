"""
Sector & Industry Analytics Engine for Bharat AI Fund Manager

Provides:
- NSE Sectors ranking (grouped by sector, sorted by avg performance)
- BSE Sectors ranking (same, separate)
- Industry ranking (combined or exchange-wise)
- Sector/Industry detail views

Data Source: yfinance t.info → sector, industry fields stored in stock_cache
"""

import pandas as pd
import numpy as np


def _compute_grouped_performance(df, group_col, exchange_filter=None):
    """
    Internal: Groups stocks by a column (sector/industry), optionally filtered by exchange.
    Returns ranked DataFrame with performance stats.
    """
    temp_df = df.copy()
    
    # Filter by exchange if specified
    if exchange_filter and "Exchange" in temp_df.columns:
        temp_df = temp_df[temp_df["Exchange"] == exchange_filter]
    
    if temp_df.empty:
        return pd.DataFrame()
    
    # Calculate individual stock performance % (if enough data)
    # Using SMA distance as proxy for recent momentum
    perf_col = "200 SMA Dist %" if "200 SMA Dist %" in temp_df.columns else None
    
    # Group by the column
    grouped = temp_df.groupby(group_col).agg(
        Stock_Count=("Ticker", "count"),
        Avg_Score=("Total Score", "mean"),
        Avg_CAGR=("Sales CAGR", "mean") if "Sales CAGR" in temp_df.columns else ("Total Score", "mean"),
        Avg_SMA_Dist=("200 SMA Dist %", "mean") if perf_col else ("Price", "mean"),
        Avg_Price=("Price", "mean"),
        Star_Stocks=("Total Star Rating", lambda x: (x >= 12).sum()),
        Turnaround_Stocks=("Turn Around", "sum") if "Turn Around" in temp_df.columns else ("Total Score", lambda x: 0)
    ).reset_index()
    
    # Rename columns for display
    col_rename = {
        group_col: group_col,
        "Stock_Count": "Stocks",
        "Avg_Score": "Avg Score",
        "Avg_CAGR": "Avg CAGR %",
        "Avg_SMA_Dist": "Avg SMA Dist %",
        "Avg_Price": "Avg Price",
        "Star_Stocks": "Star Stocks",
        "Turnaround_Stocks": "Turn Around"
    }
    grouped = grouped.rename(columns=col_rename)
    
    # Round numeric columns
    for c in ["Avg Score", "Avg CAGR %", "Avg SMA Dist %", "Avg Price"]:
        if c in grouped.columns:
            grouped[c] = grouped[c].round(2)
    
    # Rank by Avg Score descending
    grouped = grouped.sort_values("Avg Score", ascending=False).reset_index(drop=True)
    grouped["Rank"] = range(1, len(grouped) + 1)
    
    # Performance label
    grouped["Performance"] = grouped["Avg SMA Dist %"].apply(
        lambda x: "✅ Strong" if x > 10 else ("📈 Positive" if x > 0 else ("📉 Negative" if x > -10 else "🔴 Weak"))
    )
    
    return grouped


def compute_nse_sectors(df):
    """Returns NSE sector ranking DataFrame."""
    result = _compute_grouped_performance(df, "Sector", exchange_filter="NSE")
    if not result.empty:
        result.insert(0, "Exchange", "NSE")
    return result


def compute_bse_sectors(df):
    """Returns BSE sector ranking DataFrame."""
    result = _compute_grouped_performance(df, "Sector", exchange_filter="BSE")
    if not result.empty:
        result.insert(0, "Exchange", "BSE")
    return result


def compute_all_sectors(df):
    """Returns combined sector ranking (both exchanges)."""
    result = _compute_grouped_performance(df, "Sector")
    return result


def compute_nse_industries(df):
    """Returns NSE industry ranking DataFrame."""
    result = _compute_grouped_performance(df, "Industry", exchange_filter="NSE")
    if not result.empty:
        result.insert(0, "Exchange", "NSE")
    return result


def compute_bse_industries(df):
    """Returns BSE industry ranking DataFrame."""
    result = _compute_grouped_performance(df, "Industry", exchange_filter="BSE")
    if not result.empty:
        result.insert(0, "Exchange", "BSE")
    return result


def compute_all_industries(df):
    """Returns combined industry ranking."""
    result = _compute_grouped_performance(df, "Industry")
    return result


def get_sector_stocks(df, sector_name, exchange=None):
    """Returns all stocks in a given sector, optionally filtered by exchange."""
    temp = df[df["Sector"] == sector_name].copy()
    if exchange and "Exchange" in temp.columns:
        temp = temp[temp["Exchange"] == exchange]
    return temp


def get_industry_stocks(df, industry_name, exchange=None):
    """Returns all stocks in a given industry, optionally filtered by exchange."""
    temp = df[df["Industry"] == industry_name].copy()
    if exchange and "Exchange" in temp.columns:
        temp = temp[temp["Exchange"] == exchange]
    return temp


def get_sector_summary_stats(df):
    """Returns summary stats: total sectors, total industries, top sector info."""
    stats = {}
    
    sectors = df["Sector"].unique() if "Sector" in df.columns else []
    industries = df["Industry"].unique() if "Industry" in df.columns else []
    
    stats["total_sectors"] = len(sectors)
    stats["total_industries"] = len(industries)
    
    # NSE-specific
    nse_df = df[df["Exchange"] == "NSE"] if "Exchange" in df.columns else pd.DataFrame()
    bse_df = df[df["Exchange"] == "BSE"] if "Exchange" in df.columns else pd.DataFrame()
    
    stats["nse_sectors"] = len(nse_df["Sector"].unique()) if not nse_df.empty else 0
    stats["bse_sectors"] = len(bse_df["Sector"].unique()) if not bse_df.empty else 0
    stats["nse_stocks"] = len(nse_df)
    stats["bse_stocks"] = len(bse_df)
    
    # Top sector by avg score
    if not df.empty and "Sector" in df.columns:
        sector_avg = df.groupby("Sector")["Total Score"].mean()
        if not sector_avg.empty:
            stats["top_sector"] = sector_avg.idxmax()
            stats["top_sector_score"] = round(sector_avg.max(), 2)
            stats["worst_sector"] = sector_avg.idxmin()
            stats["worst_sector_score"] = round(sector_avg.min(), 2)
    
    return stats


def compute_exchange_summary(df):
    """NSE vs BSE comparison summary."""
    if "Exchange" not in df.columns:
        return pd.DataFrame()
    
    summary = df.groupby("Exchange").agg(
        Stocks=("Ticker", "count"),
        Avg_Score=("Total Score", "mean"),
        Avg_Price=("Price", "mean"),
        Star_Stocks=("Total Star Rating", lambda x: (x >= 12).sum())
    ).reset_index()
    
    summary.columns = ["Exchange", "Stocks", "Avg Score", "Avg Price", "Star Stocks"]
    for c in ["Avg Score", "Avg Price"]:
        summary[c] = summary[c].round(2)
    
    return summary
