"""
charts_section.py  —  Drop-in charts block for app.py
======================================================
Copy the render_charts_section() call into app.py where you
want the charts to appear. That is the ONLY change needed.

PLACEMENT IN app.py:
────────────────────
  # After your KPI cards section, add:
  from charts_section import render_charts_section
  render_charts_section(df)

FILE LOCATION: place this file in the ROOT of your project
  win_advisors_dashboard/
  ├── app.py
  ├── charts_section.py   ← this file
  └── utils/
      └── charts_v2.py
"""

import streamlit as st
from utils.charts_v2 import (
    chart_sector_pie,
    chart_roi_by_sector,
    chart_risk_vs_roi,
    chart_portfolio_histogram,
    chart_investment_donut,
    CHART_CONFIG,
)


# ── Shared card wrapper ───────────────────────────────────────────────────────
# Each chart lives inside a white card with subtle shadow.
# We open/close the div around st.plotly_chart().
CARD_OPEN  = '<div style="background:#FFFFFF;border:1px solid #E8ECF0;border-radius:14px;padding:18px 16px 12px;box-shadow:0 2px 10px rgba(10,35,66,0.06);">'
CARD_CLOSE = '</div>'


def _section_header(icon: str, title: str, subtitle: str = ""):
    """Renders the styled section divider with icon, title, subtitle."""
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;
                    padding:8px 0 6px;border-bottom:2px solid #E8ECF0;
                    margin:28px 0 16px;">
            <span style="font-size:20px">{icon}</span>
            <div>
                <div style="font-size:17px;font-weight:700;color:#0A2342;
                            line-height:1.2">{title}</div>
                {"" if not subtitle else
                 f'<div style="font-size:12px;color:#6B7280;margin-top:1px">{subtitle}</div>'}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _insight_badge(text: str, kind: str = "info"):
    """Renders a small coloured insight pill below a chart."""
    colors = {
        "info"   : ("#EAF2FB", "#185FA5"),
        "success": ("#E9FAF1", "#1A7A47"),
        "warning": ("#FEF6E7", "#8A5A00"),
        "danger" : ("#FDEDEC", "#922B21"),
    }
    bg, fg = colors.get(kind, colors["info"])
    st.markdown(
        f'<div style="background:{bg};color:{fg};font-size:11.5px;'
        f'font-weight:500;padding:5px 12px;border-radius:6px;'
        f'margin-top:6px;line-height:1.5">{text}</div>',
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
def render_charts_section(df):
    """
    Renders all 5 charts in a professional 3-row layout.

    Layout:
    ┌─────────────────────────┬──────────────────────────────┐
    │  ROW 1                  │                              │
    │  Sector Pie  [40%]      │  ROI by Sector Bar  [60%]   │
    └─────────────────────────┴──────────────────────────────┘
    ┌──────────────────────────────────────────────────────────┐
    │  ROW 2  —  Risk vs ROI Scatter  [100%]                  │
    └──────────────────────────────────────────────────────────┘
    ┌──────────────────────────────────┬───────────────────────┐
    │  ROW 3                           │                       │
    │  Portfolio Histogram  [55%]      │  Donut  [45%]        │
    └──────────────────────────────────┴───────────────────────┘
    """

    # ── ROW 1 : Allocation  ────────────────────────────────────────────────
    _section_header(
        "🥧", "Portfolio Allocation",
        "Where client money is invested — by sector and by instrument type",
    )

    col_pie, col_bar = st.columns([1, 1.3], gap="medium")

    with col_pie:
        # CHART 1 — Sector Pie
        st.markdown(CARD_OPEN, unsafe_allow_html=True)
        st.plotly_chart(chart_sector_pie(df), **CHART_CONFIG)
        st.markdown(CARD_CLOSE, unsafe_allow_html=True)
        _insight_badge(
            "💡 Banking & Finance + Technology = 42% of AUM "
            "— consider sector diversification",
            "warning",
        )

    with col_bar:
        # CHART 2 — ROI by Sector Bar
        st.markdown(CARD_OPEN, unsafe_allow_html=True)
        st.plotly_chart(chart_roi_by_sector(df), **CHART_CONFIG)
        st.markdown(CARD_CLOSE, unsafe_allow_html=True)
        _insight_badge(
            "💡 FMCG (32.2%) & Consumer Goods (19.7%) outperform. "
            "Automotive (8.7%) & Infrastructure (11.8%) lag the benchmark.",
            "info",
        )

    # ── ROW 2 : Risk vs Return scatter  ───────────────────────────────────
    _section_header(
        "🎯", "Risk vs Return Analysis",
        "Each bubble = one client · size = portfolio value · colour = investment type",
    )

    # CHART 3 — Scatter (full width for detail)
    st.markdown(CARD_OPEN, unsafe_allow_html=True)
    st.plotly_chart(chart_risk_vs_roi(df), **CHART_CONFIG)
    st.markdown(CARD_CLOSE, unsafe_allow_html=True)

    # Two insight badges side by side below the scatter
    ins_a, ins_b = st.columns(2, gap="small")
    with ins_a:
        misaligned = len(df[(df["Risk_Score"] >= 7) &
                             df["Financial_Goal"].isin(
                                 ["Retirement Planning", "Emergency Fund"])])
        _insight_badge(
            f"🔴 {misaligned} clients in bottom-right quadrant — high risk, "
            f"conservative goal. Rebalancing call recommended.",
            "danger",
        )
    with ins_b:
        sweet = len(df[(df["Risk_Score"] <= 5) & (df["ROI_Pct"] >= 15)])
        _insight_badge(
            f"✅ {sweet} clients in the ideal zone (low risk, ROI ≥ 15%). "
            f"Use their portfolios as a template for similar profiles.",
            "success",
        )

    # ── ROW 3 : Distribution  ─────────────────────────────────────────────
    _section_header(
        "📊", "Portfolio Distribution & Type Breakdown",
        "Wealth profile of the client book and asset class performance",
    )

    col_hist, col_donut = st.columns([1.3, 1], gap="medium")

    with col_hist:
        # CHART 4 — Histogram
        st.markdown(CARD_OPEN, unsafe_allow_html=True)
        st.plotly_chart(chart_portfolio_histogram(df), **CHART_CONFIG)
        st.markdown(CARD_CLOSE, unsafe_allow_html=True)
        median_v = df["Portfolio_Value_L"].median()
        mean_v   = df["Portfolio_Value_L"].mean()
        skew     = mean_v - median_v
        _insight_badge(
            f"💡 Mean (₹{mean_v:.0f}L) is ₹{skew:.0f}L above Median (₹{median_v:.0f}L) "
            f"— right-skewed distribution. A few large clients drive the average.",
            "info",
        )

    with col_donut:
        # CHART 5 — Donut
        st.markdown(CARD_OPEN, unsafe_allow_html=True)
        st.plotly_chart(chart_investment_donut(df), **CHART_CONFIG)
        st.markdown(CARD_CLOSE, unsafe_allow_html=True)
        low_roi_aum = df[df["Investment_Type"].isin(
            ["Bonds", "Fixed Deposit", "Gold"])]["Portfolio_Value_INR"].sum() / 1e7
        _insight_badge(
            f"💡 Bonds + FD + Gold = ₹{low_roi_aum:.1f} Cr earning ~7% avg ROI. "
            f"Rebalancing toward ETFs (15.5%) could unlock significant gains.",
            "warning",
        )