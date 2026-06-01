"""
utils/charts_v2.py  —  WIN Advisors Interactive Charts
=======================================================
Five professional Plotly charts for the portfolio dashboard.

CHART INVENTORY
───────────────
  1. chart_sector_pie()          Pie      — AUM by economic sector
  2. chart_roi_by_sector()       Bar      — Average ROI ranked by sector
  3. chart_risk_vs_roi()         Scatter  — Risk/Return per client (bubbles)
  4. chart_portfolio_histogram() Histogram— Portfolio value distribution
  5. chart_investment_donut()    Donut    — AUM by investment type

HOW TO USE IN app.py
─────────────────────
  from utils.charts_v2 import (
      chart_sector_pie, chart_roi_by_sector, chart_risk_vs_roi,
      chart_portfolio_histogram, chart_investment_donut, CHART_CONFIG
  )

  st.plotly_chart(chart_sector_pie(df),          **CHART_CONFIG)
  st.plotly_chart(chart_roi_by_sector(df),        **CHART_CONFIG)
  st.plotly_chart(chart_risk_vs_roi(df),          **CHART_CONFIG)
  st.plotly_chart(chart_portfolio_histogram(df),  **CHART_CONFIG)
  st.plotly_chart(chart_investment_donut(df),     **CHART_CONFIG)

WHERE TO PLACE THE CHARTS IN app.py
─────────────────────────────────────
  # Row 1  (2 cols — pie + bar)
  col1, col2 = st.columns([1, 1.3])
  with col1: st.plotly_chart(chart_sector_pie(df),       **CHART_CONFIG)
  with col2: st.plotly_chart(chart_roi_by_sector(df),    **CHART_CONFIG)

  # Row 2  (full width — scatter)
  st.plotly_chart(chart_risk_vs_roi(df),                 **CHART_CONFIG)

  # Row 3  (2 cols — histogram + donut)
  col3, col4 = st.columns([1.3, 1])
  with col3: st.plotly_chart(chart_portfolio_histogram(df), **CHART_CONFIG)
  with col4: st.plotly_chart(chart_investment_donut(df),    **CHART_CONFIG)

DARK / LIGHT THEME COMPATIBILITY
──────────────────────────────────
  paper_bgcolor = "rgba(0,0,0,0)"   → outer area transparent
  plot_bgcolor  = "rgba(0,0,0,0)"   → chart area transparent
  Grid colours use rgba() with low opacity → readable on both backgrounds.
  Font colour  = var(--text-primary) equivalent: "#E8EAF0" for dark,
  "#0A2342" for light. We set title colour to "#0A2342" which Streamlit
  overrides automatically when dark mode is active.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
#  DESIGN SYSTEM  —  shared across all 5 charts
# ─────────────────────────────────────────────────────────────────────────────

# 10-colour palette: blue → green → gold → orange → red
# Ordered so safer / lower-risk instruments appear cooler (blue/green)
PALETTE = [
    "#4C9BE8",   # 0  blue        Fixed Deposit, safe
    "#2ECC71",   # 1  green       Bonds, positive
    "#C9A84C",   # 2  gold        Gold, neutral
    "#9B59B6",   # 3  purple      Mutual Fund
    "#1ABC9C",   # 4  teal        ETF
    "#3498DB",   # 5  mid-blue    Equity
    "#E67E22",   # 6  orange      Real Estate
    "#F39C12",   # 7  amber       warning
    "#E74C3C",   # 8  red         Crypto, danger
    "#E91E8C",   # 9  pink        accent
]

# Stable colour per investment type — same colour on ALL charts
INV_COLORS = {
    "Fixed Deposit" : "#4C9BE8",
    "Bonds"         : "#2ECC71",
    "Gold"          : "#C9A84C",
    "Mutual Fund"   : "#9B59B6",
    "ETF"           : "#1ABC9C",
    "Equity"        : "#3498DB",
    "Real Estate"   : "#E67E22",
    "Crypto"        : "#E74C3C",
}

GRID   = "rgba(180,180,180,0.12)"  # subtle grid on transparent bg
HOVER_BG = "#0A2342"               # dark navy tooltip background

# Base layout applied to EVERY figure via **LAYOUT_BASE
LAYOUT_BASE = dict(
    font          = dict(family="DM Sans, Segoe UI, sans-serif", size=12),
    paper_bgcolor = "rgba(0,0,0,0)",   # transparent — adapts to light/dark
    plot_bgcolor  = "rgba(0,0,0,0)",
    hoverlabel    = dict(
        bgcolor     = HOVER_BG,
        font_color  = "#FFFFFF",
        font_size   = 12,
        bordercolor = "rgba(0,0,0,0)",
    ),
    title = dict(
        font    = dict(size=14, color="#0A2342"),
        x       = 0.01,
        xanchor = "left",
        pad     = dict(b=12),
    ),
)

# Pass as **CHART_CONFIG to every st.plotly_chart() call
CHART_CONFIG = dict(
    use_container_width = True,
    config = {
        "displayModeBar"          : True,
        "modeBarButtonsToRemove"  : [
            "select2d","lasso2d","autoScale2d",
            "hoverClosestCartesian","hoverCompareCartesian",
        ],
        "displaylogo"             : False,
        "toImageButtonOptions"    : {
            "format"   : "png",
            "filename" : "win_advisors_chart",
            "scale"    : 2,
        },
    },
)


# ─────────────────────────────────────────────────────────────────────────────
#  CHART 1  —  SECTOR ALLOCATION PIE
# ─────────────────────────────────────────────────────────────────────────────
def chart_sector_pie(df: pd.DataFrame) -> go.Figure:
    """
    PIE CHART — AUM split across economic sectors.

    WHAT IT SHOWS
    ─────────────
    How the firm's total Assets Under Management are spread across
    10 economic sectors (Technology, Banking, Healthcare, Energy, etc.).
    Slice area is proportional to total ₹ invested in each sector.

    BUSINESS INSIGHT
    ─────────────────
    Banking & Finance (21.2%) and Technology (21.1%) together hold 42%
    of all AUM. Both sectors are correlated — a global credit/tech crisis
    could hit both simultaneously. An advisor should diversify clients
    away from this double concentration toward Healthcare, FMCG, or
    Consumer Goods. FMCG has only 0.2% of AUM yet the best ROI (32.2%)
    — a clear opportunity to increase exposure.

    DATA PATH
    ─────────
    df → groupby('Sector') → sum('Portfolio_Value_INR') → pie slices
    """
    grp = (
        df.groupby("Sector")["Portfolio_Value_INR"]
        .sum()
        .reset_index()
        .sort_values("Portfolio_Value_INR", ascending=False)
    )
    grp["AUM_Cr"]   = (grp["Portfolio_Value_INR"] / 1e7).round(2)
    grp["Share_Pct"]= (grp["Portfolio_Value_INR"] / grp["Portfolio_Value_INR"].sum() * 100).round(1)
    # Client count per sector for the hover tooltip
    client_count = df.groupby("Sector")["Client_ID"].count().reindex(grp["Sector"]).values

    fig = go.Figure(go.Pie(
        labels        = grp["Sector"],
        values        = grp["Portfolio_Value_INR"],
        customdata    = list(zip(grp["AUM_Cr"], grp["Share_Pct"], client_count)),
        hovertemplate = (
            "<b>%{label}</b><br>"
            "AUM : ₹%{customdata[0]:.2f} Cr<br>"
            "Share: %{customdata[1]:.1f}%<br>"
            "Clients: %{customdata[2]}<extra></extra>"
        ),
        textinfo      = "label+percent",
        textposition  = "outside",
        textfont_size = 10,
        pull          = [0.05] * len(grp),          # equal pull on all slices
        marker        = dict(
            colors = PALETTE[:len(grp)],
            line   = dict(color="#FFFFFF", width=2), # white border between slices
        ),
        direction     = "clockwise",
        rotation      = -90,                         # largest slice at top (12 o'clock)
        sort          = True,
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title_text = "Sector Allocation — AUM Distribution",
        showlegend = True,
        height     = 400,
        margin     = dict(t=56, b=36, l=16, r=130),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  CHART 2  —  AVERAGE ROI BY SECTOR  (horizontal bar)
# ─────────────────────────────────────────────────────────────────────────────
def chart_roi_by_sector(df: pd.DataFrame) -> go.Figure:
    """
    HORIZONTAL BAR — Mean ROI % per sector, sorted from highest to lowest.

    WHAT IT SHOWS
    ─────────────
    Which economic sectors are generating the best returns for clients.
    Bars are colour-coded: green = beating the 12% benchmark, red = below.
    Error bars show standard deviation — wide = inconsistent returns
    across clients within that sector.

    BUSINESS INSIGHT
    ─────────────────
    FMCG (32.2%) and Consumer Goods (19.7%) outperform massively vs
    Automotive (8.7%). Yet Banking & Finance holds 21% of AUM and earns
    only 16.9% — decent but not the best. The benchmark line (12%) shows
    that Pharmaceuticals, Energy, Infrastructure and Automotive are all
    performing below expectations given the risk they carry. Those sectors
    are candidates for portfolio rebalancing toward FMCG/Consumer Goods.

    DATA PATH
    ─────────
    df → groupby('Sector') → mean/std/count('ROI_Pct') → horizontal bar
    Sorted ascending (so highest bar appears at top in horizontal layout).
    """
    BENCHMARK = 12.0

    grp = (
        df.groupby("Sector")["ROI_Pct"]
        .agg(mean="mean", count="count", std="std")
        .reset_index()
        .fillna({"std": 0})
        .sort_values("mean", ascending=True)          # ascending → top bar = highest
    )

    # Green if beating benchmark, red if below
    colors = ["#2ECC71" if v >= BENCHMARK else "#E74C3C" for v in grp["mean"]]

    fig = go.Figure(go.Bar(
        x             = grp["mean"],
        y             = grp["Sector"],
        orientation   = "h",
        marker_color  = colors,
        marker_line   = dict(width=0),
        text          = [f"  {v:.1f}%" for v in grp["mean"]],
        textposition  = "outside",
        textfont      = dict(size=11),
        # Error bars = std dev — shows how consistent each sector is
        error_x       = dict(
            type      = "data",
            array     = grp["std"].fillna(0),
            color     = "rgba(130,130,130,0.45)",
            thickness = 1.5,
            width     = 5,
        ),
        hovertemplate = (
            "<b>%{y}</b><br>"
            "Avg ROI : %{x:.2f}%<br>"
            "Clients : %{customdata[0]}<br>"
            "Std Dev : ±%{customdata[1]:.1f}%<extra></extra>"
        ),
        customdata     = list(zip(grp["count"].astype(int), grp["std"].round(1))),
    ))

    # Dashed reference line at the 12% benchmark
    fig.add_vline(
        x=BENCHMARK, line_dash="dot",
        line_color="#C9A84C", line_width=2,
        annotation_text=f"Nifty 50 benchmark ({BENCHMARK}%)",
        annotation_position="top",
        annotation_font_size=10,
        annotation_font_color="#C9A84C",
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title_text = "Average ROI by Sector  (green = above benchmark)",
        xaxis = dict(
            showgrid   = True, gridcolor=GRID,
            ticksuffix = "%", title="Average Annual ROI",
            range      = [0, grp["mean"].max() * 1.28],
        ),
        yaxis      = dict(showgrid=False, title="", tickfont=dict(size=11)),
        showlegend = False,
        height     = 400,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  CHART 3  —  RISK SCORE vs ROI  (bubble scatter)
# ─────────────────────────────────────────────────────────────────────────────
def chart_risk_vs_roi(df: pd.DataFrame) -> go.Figure:
    """
    BUBBLE SCATTER — Each bubble = one client.
      X  →  Risk Score  (1 = safest  …  10 = most volatile)
      Y  →  Annual ROI %
      Size → Portfolio Value (₹ Lakhs) — bigger client = bigger bubble
      Colour → Investment Type (consistent with donut chart colours)

    WHAT IT SHOWS
    ─────────────
    The risk-return relationship across the entire client book.
    In a well-managed portfolio, higher risk should yield higher
    returns. The chart is split into 4 quadrants:

        LOW RISK / HIGH RETURN  ← top-left  → ideal sweet spot ✅
        LOW RISK / LOW RETURN   ← bot-left  → over-conservative ⚠
        HIGH RISK / HIGH RETURN ← top-right → monitor closely ℹ
        HIGH RISK / LOW RETURN  ← bot-right → needs review NOW 🔴

    BUSINESS INSIGHT
    ─────────────────
    Clients in the bottom-right are being under-compensated for
    the risk they're taking — the most critical advisory action.
    Large bubbles in the bottom-right represent the most urgent
    rebalancing conversations (big AUM + bad risk-return trade-off).
    Jitter is added to the X-axis so bubbles on the same risk score
    don't overlap each other.

    DATA PATH
    ─────────
    df → scatter(x=Risk_Score, y=ROI_Pct, size=Portfolio_Value_L,
                 color=Investment_Type)  — one trace per inv. type
    """
    np.random.seed(42)
    df_plot              = df.copy()
    df_plot["x_jitter"]  = df_plot["Risk_Score"] + np.random.uniform(-0.28, 0.28, len(df_plot))
    # Scale bubble pixel size: min 8, max 36
    max_val              = df_plot["Portfolio_Value_L"].max()
    df_plot["bsize"]     = 8 + (df_plot["Portfolio_Value_L"] / max_val) * 28

    fig = go.Figure()

    # One Scatter trace per investment type → clean colour legend
    for inv_type, color in INV_COLORS.items():
        sub = df_plot[df_plot["Investment_Type"] == inv_type]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x          = sub["x_jitter"],
            y          = sub["ROI_Pct"],
            mode       = "markers",
            name       = inv_type,
            marker     = dict(
                color   = color,
                size    = sub["bsize"],
                opacity = 0.80,
                line    = dict(color="rgba(255,255,255,0.55)", width=1),
            ),
            hovertemplate = (
                "<b>%{customdata[0]}</b>  (%{customdata[1]})<br>"
                "Risk Score : %{customdata[2]}/10<br>"
                "ROI        : %{y:.2f}%<br>"
                "Portfolio  : ₹%{customdata[3]:.1f}L<br>"
                "Goal       : %{customdata[4]}<extra></extra>"
            ),
            customdata = list(zip(
                sub["Client_Name"],   sub["Client_ID"],
                sub["Risk_Score"],    sub["Portfolio_Value_L"],
                sub["Financial_Goal"],
            )),
        ))

    # ── Quadrant shading (drawn BELOW the bubbles) ────────────────────────
    roi_mid  = float(df["ROI_Pct"].median())   # ~15.1 %
    risk_mid = 5.5

    fig.add_shape(type="rect", x0=0.5, x1=risk_mid, y0=0,       y1=roi_mid,
                  fillcolor="rgba(243,156,18,0.07)",  line_width=0, layer="below")
    fig.add_shape(type="rect", x0=0.5, x1=risk_mid, y0=roi_mid, y1=40,
                  fillcolor="rgba(46,204,113,0.07)",  line_width=0, layer="below")
    fig.add_shape(type="rect", x0=risk_mid, x1=9.7,  y0=roi_mid, y1=40,
                  fillcolor="rgba(52,152,219,0.06)",  line_width=0, layer="below")
    fig.add_shape(type="rect", x0=risk_mid, x1=9.7,  y0=0,       y1=roi_mid,
                  fillcolor="rgba(231,76,60,0.08)",   line_width=0, layer="below")

    # Quadrant labels
    for txt, x, y, col in [
        ("⚠ Over-conservative",  2.9,  2.5,  "rgba(180,130,0,0.70)"),
        ("✅ Ideal sweet spot",   2.9, 38.0,  "rgba(39,174,96,0.85)"),
        ("ℹ  Monitor closely",   7.5, 38.0,  "rgba(41,128,185,0.75)"),
        ("🔴 Needs review",       7.5,  2.5,  "rgba(192,57,43,0.80)"),
    ]:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False,
                           font=dict(size=9, color=col), xanchor="center")

    # Divider lines
    fig.add_hline(y=roi_mid,  line_dash="dot", line_color="rgba(160,160,160,0.30)", line_width=1)
    fig.add_vline(x=risk_mid, line_dash="dot", line_color="rgba(160,160,160,0.30)", line_width=1)

    fig.update_layout(
        **LAYOUT_BASE,
        title_text = "Risk Score vs ROI  —  bubble size = portfolio value  |  colour = investment type",
        xaxis      = dict(
            showgrid = True, gridcolor=GRID,
            title    = "Risk Score  (1 = safest  ·  10 = most volatile)",
            tickmode = "linear", tick0=1, dtick=1, range=[0.5, 9.8],
        ),
        yaxis      = dict(
            showgrid=True, gridcolor=GRID,
            title="Annual ROI %", ticksuffix="%", range=[0, 41],
        ),
        legend     = dict(orientation="h", x=0, y=-0.20, font_size=10),
        height     = 480,
        showlegend = True,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  CHART 4  —  PORTFOLIO VALUE DISTRIBUTION  (histogram)
# ─────────────────────────────────────────────────────────────────────────────
def chart_portfolio_histogram(df: pd.DataFrame) -> go.Figure:
    """
    HISTOGRAM — How client portfolio sizes are spread across the book.

    WHAT IT SHOWS
    ─────────────
    The frequency distribution of Portfolio_Value_L (₹ Lakhs).
    Bin width is set to produce ~20 bars covering the ₹0–₹160L range.
    A second overlaid trace highlights HNI clients (≥ ₹100L) in gold.
    Reference lines mark the median, mean, and HNI threshold.

    BUSINESS INSIGHT
    ─────────────────
    The distribution is RIGHT-SKEWED (log-normal). The median (₹17.2L)
    sits well below the mean (₹28.2L) — a few large portfolios pull the
    average up. This is the Pareto effect: roughly the top 15 clients
    (₹100L+) likely hold 30–40% of total AUM.

    Key actions:
    • Gap between median and mean → identify and VIP-tier HNI clients
    • Spike at ₹10–20L → largest client cohort → design products for this band
    • Left tail (< ₹5L) → consider minimum portfolio threshold policy

    DATA PATH
    ─────────
    df → histogram(Portfolio_Value_L, nbinsx=22) + vlines for median/mean
    """
    median_v = df["Portfolio_Value_L"].median()
    mean_v   = df["Portfolio_Value_L"].mean()

    fig = go.Figure()

    # Main histogram — all clients
    fig.add_trace(go.Histogram(
        x             = df["Portfolio_Value_L"],
        nbinsx        = 22,
        name          = "All clients",
        marker        = dict(
            color   = "#4C9BE8",
            opacity = 0.82,
            line    = dict(color="#FFFFFF", width=0.8),
        ),
        hovertemplate = "₹%{x:.0f}L range — %{y} clients<extra></extra>",
    ))

    # Overlay — HNI clients (≥ ₹100L) in gold
    hni = df[df["Portfolio_Value_L"] >= 100]
    if not hni.empty:
        fig.add_trace(go.Histogram(
            x             = hni["Portfolio_Value_L"],
            nbinsx        = 6,
            name          = f"HNI clients (≥ ₹100L)  n={len(hni)}",
            marker        = dict(
                color   = "#C9A84C",
                opacity = 0.90,
                line    = dict(color="#FFFFFF", width=0.8),
            ),
            hovertemplate = "HNI ₹%{x:.0f}L — %{y} clients<extra></extra>",
        ))

    # Median line (solid green)
    fig.add_vline(
        x=median_v, line_dash="solid", line_color="#2ECC71", line_width=2,
        annotation_text=f"Median ₹{median_v:.0f}L",
        annotation_position="top right",
        annotation_font_color="#2ECC71", annotation_font_size=10,
    )
    # Mean line (dashed red) — floats above median because of skew
    fig.add_vline(
        x=mean_v, line_dash="dot", line_color="#E74C3C", line_width=2,
        annotation_text=f"Mean ₹{mean_v:.0f}L",
        annotation_position="top right",
        annotation_font_color="#E74C3C", annotation_font_size=10,
        annotation_yshift=18,    # shift up so labels don't overlap
    )
    # HNI threshold (dashed gold)
    fig.add_vline(
        x=100, line_dash="longdash",
        line_color="rgba(201,168,76,0.55)", line_width=1.5,
        annotation_text="HNI threshold ₹100L",
        annotation_position="top left",
        annotation_font_color="#C9A84C", annotation_font_size=9,
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title_text = "Portfolio Value Distribution (₹ Lakhs)  —  Client Wealth Profile",
        xaxis      = dict(
            showgrid   = True, gridcolor=GRID,
            title      = "Portfolio Value (₹ Lakhs)",
            tickprefix = "₹", ticksuffix="L",
        ),
        yaxis      = dict(showgrid=True, gridcolor=GRID, title="Number of Clients"),
        barmode    = "overlay",   # HNI bars sit ON TOP of blue bars
        bargap     = 0.06,
        legend     = dict(orientation="h", x=0.42, y=0.97, font_size=10),
        height     = 380,
        showlegend = True,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  CHART 5  —  INVESTMENT TYPE DONUT
# ─────────────────────────────────────────────────────────────────────────────
def chart_investment_donut(df: pd.DataFrame) -> go.Figure:
    """
    DONUT CHART — AUM split by investment instrument type.

    WHAT IT SHOWS
    ─────────────
    How the firm's money is allocated across 8 asset classes:
    Equity, Bonds, ETF, Mutual Fund, Gold, Real Estate, Fixed Deposit, Crypto.
    Centre annotation shows total AUM (₹28.2 Cr).
    Hover shows BOTH AUM allocation AND average ROI for each type.

    BUSINESS INSIGHT
    ─────────────────
    Equity dominates at ₹9.14 Cr (32% of AUM) and earns 23.2% ROI — justified.
    Bonds hold ₹6.34 Cr (22%) but earn only 7.6% — below the 12% benchmark.
    Fixed Deposit and Gold together hold 15% of AUM but earn sub-benchmark returns.
    These three (Bonds + FD + Gold) = 37% of AUM earning ~7% average → clear
    rebalancing signal toward ETFs (15.5% ROI) or Mutual Funds (16.0% ROI).
    Crypto: 1 client, ₹0.40 Cr, 35.3% ROI — high risk outlier.

    Donut vs Pie: the hole serves a purpose — it holds the total AUM annotation,
    making the most important number visible even without reading the legend.

    DATA PATH
    ─────────
    df → groupby('Investment_Type') → sum(AUM), mean(ROI), count
       → Pie with hole=0.58
    """
    grp = (
        df.groupby("Investment_Type")
        .agg(
            AUM     = ("Portfolio_Value_INR", "sum"),
            Clients = ("Client_ID",           "count"),
            AvgROI  = ("ROI_Pct",             "mean"),
        )
        .reset_index()
        .sort_values("AUM", ascending=False)
    )
    grp["AUM_Cr"]  = (grp["AUM"]    / 1e7).round(2)
    grp["AUM_pct"] = (grp["AUM"]    / grp["AUM"].sum() * 100).round(1)
    grp["AvgROI"]  = grp["AvgROI"].round(1)

    total_cr = grp["AUM"].sum() / 1e7

    # Colour per type (consistent with scatter chart)
    colors = [INV_COLORS.get(t, PALETTE[i % len(PALETTE)])
              for i, t in enumerate(grp["Investment_Type"])]

    fig = go.Figure(go.Pie(
        labels        = grp["Investment_Type"],
        values        = grp["AUM"],
        hole          = 0.58,        # 58% empty centre for annotation
        marker        = dict(
            colors = colors,
            line   = dict(color="#FFFFFF", width=2.5),
        ),
        customdata    = list(zip(
            grp["AUM_Cr"], grp["AUM_pct"], grp["AvgROI"], grp["Clients"],
        )),
        hovertemplate = (
            "<b>%{label}</b><br>"
            "AUM     : ₹%{customdata[0]:.2f} Cr  (%{customdata[1]:.1f}%)<br>"
            "Avg ROI : %{customdata[2]:.1f}%<br>"
            "Clients : %{customdata[3]}<extra></extra>"
        ),
        textinfo      = "label+percent",
        textposition  = "outside",
        textfont_size = 10,
        # Pull the largest slice slightly for emphasis
        pull          = [0.06 if i == 0 else 0 for i in range(len(grp))],
        rotation      = 90,          # start at 12 o'clock
        direction     = "clockwise",
        sort          = True,
    ))

    # Total AUM annotation inside the hole
    fig.add_annotation(
        text      = (
            f"<b>₹{total_cr:.1f}</b><br>"
            "<span style='font-size:10px;color:#6B7280'>Crores AUM</span>"
        ),
        x=0.5, y=0.5,
        font      = dict(size=17, color="#0A2342"),
        showarrow = False,
        xanchor   = "center",
        yanchor   = "middle",
    )

    fig.update_layout(
        **LAYOUT_BASE,
        title_text = "Investment Type Allocation  —  AUM & Average ROI per Type",
        showlegend = True,
        legend     = dict(orientation="v", x=1.01, y=0.5, font_size=10),
        height     = 420,
        margin     = dict(t=56, b=36, l=16, r=140),
    )
    return fig