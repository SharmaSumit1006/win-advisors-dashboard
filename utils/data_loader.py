"""
utils/data_loader.py
--------------------
Loads and preprocesses the WIN Advisors portfolio dataset.
The @st.cache_data decorator means Streamlit reads the CSV only ONCE,
then stores it in memory — making all filter interactions instant.
"""

import pandas as pd
import streamlit as st


@st.cache_data
def load_portfolio() -> pd.DataFrame:
    """
    Load the main client portfolio CSV.
    Returns a clean, typed DataFrame ready for analysis.
    """
    df = pd.read_csv("data/win_advisors_portfolio_dataset.csv")

    # ── Type fixes ────────────────────────────────────────────────────────────
    # Risk_Score should be an integer, not float
    df["Risk_Score"] = df["Risk_Score"].astype(int)

    # Portfolio values as integer rupees
    df["Portfolio_Value_INR"] = df["Portfolio_Value_INR"].astype(int)

    # Round percentage columns to 2 decimal places for clean display
    df["Monthly_Return_Pct"] = df["Monthly_Return_Pct"].round(2)
    df["ROI_Pct"]            = df["ROI_Pct"].round(2)

    # ── Derived columns ───────────────────────────────────────────────────────
    # Risk label: converts 1–10 score into a human-readable category
    df["Risk_Label"] = df["Risk_Score"].apply(classify_risk)

    # Portfolio value in Lakhs for shorter display in charts
    df["Portfolio_Value_L"] = (df["Portfolio_Value_INR"] / 100_000).round(2)

    # Risk-adjusted return: ROI earned per unit of risk taken
    # Higher is better — a client with ROI 20% and Risk 5 scores 4.0
    df["Risk_Adj_Return"] = (df["ROI_Pct"] / df["Risk_Score"]).round(2)

    # Performance tier based on ROI
    df["Performance_Tier"] = df["ROI_Pct"].apply(classify_performance)

    return df


def classify_risk(score: int) -> str:
    """Maps numeric risk score (1–10) to a label."""
    if score <= 2:
        return "Very Low"
    elif score <= 4:
        return "Low"
    elif score <= 6:
        return "Moderate"
    elif score <= 8:
        return "High"
    else:
        return "Very High"


def classify_performance(roi: float) -> str:
    """Buckets ROI% into performance tiers for colour-coding."""
    if roi >= 20:
        return "Excellent"
    elif roi >= 12:
        return "Good"
    elif roi >= 6:
        return "Average"
    else:
        return "Below Average"


def get_kpis(df: pd.DataFrame) -> dict:
    """
    Compute the 6 headline KPIs shown in the metrics bar.
    All values are pre-formatted strings ready to drop into st.metric().
    """
    total_aum     = df["Portfolio_Value_INR"].sum()
    avg_roi       = df["ROI_Pct"].mean()
    avg_risk      = df["Risk_Score"].mean()
    top_sector    = df["Sector"].value_counts().idxmax()
    best_inv_type = df.groupby("Investment_Type")["ROI_Pct"].mean().idxmax()
    misaligned    = len(df[
        (df["Financial_Goal"].isin(["Retirement Planning", "Emergency Fund"])) &
        (df["Risk_Score"] >= 7)
    ])

    return {
        "total_aum"     : f"₹{total_aum / 1_000_000:.1f} Cr",
        "total_clients" : len(df),
        "avg_roi"       : f"{avg_roi:.1f}%",
        "avg_risk"      : f"{avg_risk:.1f} / 10",
        "top_sector"    : top_sector,
        "best_inv_type" : best_inv_type,
        "misaligned"    : misaligned,
        # Raw numbers for delta calculations
        "_avg_roi_raw"  : avg_roi,
        "_avg_risk_raw" : avg_risk,
    }


def apply_filters(df: pd.DataFrame,
                  inv_types: list,
                  risk_range: tuple,
                  regions: list,
                  goals: list) -> pd.DataFrame:
    """
    Apply all sidebar filters to the DataFrame.
    Each filter is additive (AND logic) — fewer selections = smaller result.
    """
    mask = (
        df["Investment_Type"].isin(inv_types) &
        df["Risk_Score"].between(risk_range[0], risk_range[1]) &
        df["Region"].isin(regions) &
        df["Financial_Goal"].isin(goals)
    )
    return df[mask].copy()