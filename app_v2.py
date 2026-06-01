"""
app.py  —  WIN Advisors Portfolio Dashboard  v2.0  (Enterprise Polish)
=======================================================================
UI/UX upgrade: improved typography, spacing, animations, dark theme,
loading skeletons, section hierarchy, and chart card aesthetics.

WHAT CHANGED vs v1
───────────────────
  +  inject_global_theme()   → fonts, fade-in, component overrides
  +  section_header()        → gradient accent bar + icon + subtitle
  +  divider()               → gradient hr between sections
  +  skeleton_kpi_row()      → shimmer placeholders while loading
  +  info_badge()            → coloured insight pills below charts
  +  page_footer()           → consistent branded footer
  ~  Company header          → radial glow, live-badge pulse animation
  ~  CARD_OPEN/CLOSE wrappers→ elevated shadow + 14px radius
  ~  style.css               → 700 lines, 12 sections, CSS variables
  ~  All section titles      → section_header() for consistency
"""

import streamlit as st
from datetime import datetime
import pandas as pd

# ── Core modules ──────────────────────────────────────────────────────────────
from utils.data_loader       import load_portfolio, get_kpis
from utils.sidebar_filters   import render_sidebar, apply_filters, render_filter_summary
from utils.kpi_cards         import compute_kpis, render_kpi_row
from utils.charts_v2         import (
    chart_sector_pie, chart_roi_by_sector, chart_risk_vs_roi,
    chart_portfolio_histogram, chart_investment_donut, CHART_CONFIG,
)
from utils.recommendation_engine import generate_recommendations, render_recommendations
from utils.theme import (
    inject_global_theme, section_header, divider,
    skeleton_kpi_row, skeleton_chart, info_badge,
    metric_footnote, page_footer, CARD_OPEN, CARD_CLOSE,
)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG  —  must be the very first Streamlit call
# ═════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title            = "WIN Advisors | Portfolio Dashboard",
    page_icon             = "💼",
    layout                = "wide",
    initial_sidebar_state = "expanded",
)

# ── Inject CSS + Google Fonts ─────────────────────────────────────────────────
# ORDER MATTERS: style.css first (base variables), then theme (overrides)
with open("assets/style.css", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
inject_global_theme()


# ═════════════════════════════════════════════════════════════════════════════
# DATA LAYER
# ═════════════════════════════════════════════════════════════════════════════
df_full = load_portfolio()


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR FILTERS
# ═════════════════════════════════════════════════════════════════════════════
filter_state = render_sidebar(df_full)
df           = apply_filters(df_full, filter_state)


# ═════════════════════════════════════════════════════════════════════════════
# ── SECTION: COMPANY HEADER BANNER
# ═════════════════════════════════════════════════════════════════════════════
now_str        = datetime.now().strftime("%d %b %Y · %I:%M %p")
filtered_count = len(df)
total_count    = len(df_full)
delta_str      = (
    f"All {total_count} clients"
    if filtered_count == total_count
    else f"{filtered_count} of {total_count} clients"
)

st.markdown(f"""
<div class="company-header">
    <div>
        <div style="font-size:10.5px;color:rgba(255,255,255,0.42);
                    font-weight:700;text-transform:uppercase;
                    letter-spacing:1.4px;margin-bottom:7px">
            WIN ADVISORS  ·  Portfolio Intelligence Platform
        </div>
        <h1 style="color:#FFFFFF;font-size:26px;font-weight:800;
                   margin:0;letter-spacing:-0.6px;line-height:1.2">
            Client Portfolio Dashboard
        </h1>
        <div style="color:rgba(255,255,255,0.55);font-size:12.5px;
                    margin-top:6px;font-weight:400">
            Comprehensive analytics for smarter advisory decisions
        </div>
    </div>
    <div style="text-align:right;flex-shrink:0">
        <div class="live-badge" style="margin-bottom:10px;display:inline-block">
            ● LIVE
        </div>
        <div style="color:rgba(255,255,255,0.45);font-size:11px;
                    margin-bottom:3px">{now_str}</div>
        <div style="color:rgba(201,168,76,0.85);font-size:11.5px;
                    font-weight:600">{delta_str}</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Active filter summary bar ─────────────────────────────────────────────────
render_filter_summary(df_full, df, filter_state)


# ═════════════════════════════════════════════════════════════════════════════
# ── SECTION: KPI CARDS
# ═════════════════════════════════════════════════════════════════════════════
section_header("", "Key Performance Indicators",
               f"Metrics calculated from {len(df)} filtered client records")

kpis = compute_kpis(df)
render_kpi_row(kpis)


# ═════════════════════════════════════════════════════════════════════════════
# ── SECTION: ALLOCATION ANALYSIS  (Pie + Bar)
# ═════════════════════════════════════════════════════════════════════════════
divider()
section_header("", "Portfolio Allocation",
               "AUM distribution by sector and investment type")

col_pie, col_bar = st.columns([1, 1.3], gap="medium")

with col_pie:
    st.markdown(CARD_OPEN, unsafe_allow_html=True)
    st.plotly_chart(chart_sector_pie(df), **CHART_CONFIG)
    st.markdown(CARD_CLOSE, unsafe_allow_html=True)
    info_badge(
        "Banking & Finance + Technology = 42% of AUM — monitor for correlated sector risk.",
        kind="warning", icon="",
    )

with col_bar:
    st.markdown(CARD_OPEN, unsafe_allow_html=True)
    st.plotly_chart(chart_roi_by_sector(df), **CHART_CONFIG)
    st.markdown(CARD_CLOSE, unsafe_allow_html=True)
    info_badge(
        "FMCG (32.2%) and Consumer Goods (19.7%) outperform. "
        "Automotive (8.7%) and Infrastructure (11.8%) lag the 12% benchmark.",
        kind="info", icon="",
    )


# ═════════════════════════════════════════════════════════════════════════════
# ── SECTION: RISK VS RETURN  (full-width scatter)
# ═════════════════════════════════════════════════════════════════════════════
divider()
section_header("", "Risk vs Return Analysis",
               "Each bubble = one client · bubble size = portfolio value")

st.markdown(CARD_OPEN, unsafe_allow_html=True)
st.plotly_chart(chart_risk_vs_roi(df), **CHART_CONFIG)
st.markdown(CARD_CLOSE, unsafe_allow_html=True)

# Two-column insight badges under the scatter
ins_a, ins_b = st.columns(2, gap="small")
with ins_a:
    misaligned = len(df[
        (df["Risk_Score"] >= 7) &
        df["Financial_Goal"].isin(["Retirement Planning", "Emergency Fund"])
    ])
    info_badge(
        f"{misaligned} clients in the bottom-right quadrant — high risk, "
        f"conservative goal. Immediate rebalancing call recommended.",
        kind="danger", icon="",
    )
with ins_b:
    sweet = len(df[(df["Risk_Score"] <= 5) & (df["ROI_Pct"] >= 15)])
    info_badge(
        f"{sweet} clients in the ideal zone (risk ≤ 5, ROI ≥ 15%). "
        f"Use their portfolios as a model for similar-profile onboarding.",
        kind="success", icon="",
    )


# ═════════════════════════════════════════════════════════════════════════════
# ── SECTION: DISTRIBUTION & TYPE BREAKDOWN  (Histogram + Donut)
# ═════════════════════════════════════════════════════════════════════════════
divider()
section_header("", "Distribution & Instrument Breakdown",
               "Client wealth profile and asset class performance")

col_hist, col_donut = st.columns([1.3, 1], gap="medium")

with col_hist:
    st.markdown(CARD_OPEN, unsafe_allow_html=True)
    st.plotly_chart(chart_portfolio_histogram(df), **CHART_CONFIG)
    st.markdown(CARD_CLOSE, unsafe_allow_html=True)
    median_v = df["Portfolio_Value_L"].median()
    mean_v   = df["Portfolio_Value_L"].mean()
    info_badge(
        f"Mean (₹{mean_v:.0f}L) is ₹{mean_v - median_v:.0f}L above Median (₹{median_v:.0f}L) "
        f"— right-skewed distribution driven by HNI clients.",
        kind="info", icon="",
    )

with col_donut:
    st.markdown(CARD_OPEN, unsafe_allow_html=True)
    st.plotly_chart(chart_investment_donut(df), **CHART_CONFIG)
    st.markdown(CARD_CLOSE, unsafe_allow_html=True)
    bonds_fd_gold_aum = df[
        df["Investment_Type"].isin(["Bonds", "Fixed Deposit", "Gold"])
    ]["Portfolio_Value_INR"].sum() / 1e7
    info_badge(
        f"Bonds + FD + Gold hold ₹{bonds_fd_gold_aum:.1f} Cr at ~7% avg ROI. "
        f"Rebalancing toward ETFs (15.5%) could unlock significant gains.",
        kind="warning", icon="",
    )


# ═════════════════════════════════════════════════════════════════════════════
# ── SECTION: SMART RECOMMENDATIONS
# ═════════════════════════════════════════════════════════════════════════════
divider()
section_header("", "Smart Portfolio Recommendations",
               "AI-style rule engine — re-calculates with every filter change")

recommendations = generate_recommendations(df)
render_recommendations(recommendations)


# ═════════════════════════════════════════════════════════════════════════════
# ── SECTION: CLIENT DATA TABLE
# ═════════════════════════════════════════════════════════════════════════════
divider()

with st.expander(
    f"  Client Data Table  —  {len(df)} records",
    expanded=False,
):
    metric_footnote(
        "Showing filtered dataset. Click any column header to sort. "
        "Use sidebar filters to narrow down the view."
    )

    display_cols = [
        "Client_ID", "Client_Name", "Investment_Type", "Portfolio_Value_L",
        "ROI_Pct", "Risk_Score", "Risk_Label", "Sector",
        "Region", "Financial_Goal",
    ]
    st.dataframe(
        df[display_cols].rename(columns={
            "Portfolio_Value_L": "Portfolio (₹L)",
            "ROI_Pct"          : "ROI %",
            "Risk_Score"       : "Risk",
            "Risk_Label"       : "Risk Level",
        }),
        use_container_width = True,
        height              = 400,
    )

    dl_col, spacer = st.columns([1, 3])
    with dl_col:
        st.download_button(
            label     = "⬇  Export filtered CSV",
            data      = df.to_csv(index=False).encode("utf-8"),
            file_name = f"win_advisors_portfolio_{datetime.now().strftime('%Y%m%d')}.csv",
            mime      = "text/csv",
            use_container_width=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# ── FOOTER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<hr style="margin-top:40px">
<div style="text-align:center;color:gray;font-size:13px">
WIN Advisors • Portfolio Intelligence Platform • Built with Streamlit
</div>
""", unsafe_allow_html=True)
page_footer()