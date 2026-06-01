"""
utils/kpi_cards.py
==================
Professional KPI card system for WIN Advisors Dashboard.

This module handles TWO things:
  1. compute_kpis(df)  →  calculates every number shown on the cards
  2. render_kpi_row()  →  builds the full 5-card UI in Streamlit

HOW KPI CARDS WORK IN STREAMLIT
────────────────────────────────
Streamlit's built-in st.metric() gives you a label + value + delta arrow.
We EXTEND that by injecting a custom HTML wrapper around each metric that adds:
  • A coloured top border (blue / amber / red / green)
  • An icon in the corner
  • A subtle hover lift animation
  • A trend indicator bar at the bottom

USAGE IN app.py
───────────────
    from utils.kpi_cards import compute_kpis, render_kpi_row

    df  = load_portfolio()          # load filtered DataFrame
    kpis = compute_kpis(df)         # compute all 5 KPI dictionaries
    render_kpi_row(kpis)            # draw the 5 cards side-by-side
"""

import streamlit as st
import pandas as pd


# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — KPI COMPUTATION
# Each function takes the filtered DataFrame and returns a dict with:
#   value   → the main big number shown on the card
#   delta   → comparison text shown below with ↑ or ↓
#   status  → "good" | "warning" | "danger" | "neutral"
#   detail  → one-line context shown at the bottom of the card
# ══════════════════════════════════════════════════════════════════════════════

def _kpi_total_portfolio(df: pd.DataFrame) -> dict:
    """
    KPI 1 — TOTAL PORTFOLIO VALUE
    ─────────────────────────────
    WHAT IT IS:
        Sum of Portfolio_Value_INR across all filtered clients.
        This is the firm's total Assets Under Management (AUM).

    WHY IT MATTERS:
        AUM is the most important metric in wealth management.
        Advisory firms charge a % fee on AUM, so this number
        directly determines revenue. It's the first number any
        managing director asks when they open the dashboard.

    CALCULATION:
        total = SUM(Portfolio_Value_INR)
        We simulate a previous period (+7.3% growth) to show
        a realistic quarter-on-quarter delta arrow.

    BUSINESS RULE:
        If total AUM < ₹10 Cr  → warning (small book)
        If total AUM ≥ ₹10 Cr  → good
    """
    total       = df["Portfolio_Value_INR"].sum()
    total_cr    = total / 1e7                          # convert to Crores

    # Simulate QoQ growth: real dashboards would compare to a previous period table
    prev_total  = total * (1 / 1.073)                  # implies +7.3% growth
    delta_pct   = (total - prev_total) / prev_total * 100

    # Largest single client — useful context for concentration risk
    top_client_val  = df["Portfolio_Value_INR"].max() / 1e7
    top_client_pct  = (df["Portfolio_Value_INR"].max() / total) * 100

    return {
        "label"   : "Total Portfolio Value",
        "icon"    : "💰",
        "value"   : f"₹{total_cr:.2f} Cr",
        "delta"   : f"+{delta_pct:.1f}% vs last quarter",
        "status"  : "good" if total_cr >= 10 else "warning",
        "detail"  : f"Top client holds {top_client_pct:.1f}% of AUM",
        "raw"     : total_cr,
        "delta_direction": "up",
    }


def _kpi_average_roi(df: pd.DataFrame) -> dict:
    """
    KPI 2 — AVERAGE ROI
    ────────────────────
    WHAT IT IS:
        Mean of ROI_Pct across all filtered clients.
        ROI (Return on Investment) is annualised — how much
        the portfolio has grown per year as a percentage.

    WHY IT MATTERS:
        ROI is the advisor's report card. Every client ultimately
        asks: "Is my money growing?" ROI answers that.
        We compare against the Nifty 50 benchmark (~12% annual)
        to show whether the portfolio is beating the market.

    CALCULATION:
        avg_roi         = MEAN(ROI_Pct)
        benchmark       = 12.0  (Nifty 50 long-run average)
        alpha           = avg_roi - benchmark  (excess return)

    BUSINESS RULE:
        alpha > 0    → good  (beating the market)
        -3 < alpha ≤ 0 → warning  (slightly below market)
        alpha ≤ -3   → danger  (significantly underperforming)
    """
    avg_roi   = df["ROI_Pct"].mean()
    benchmark = 12.0
    alpha     = avg_roi - benchmark

    # Distribution context
    above_bench = len(df[df["ROI_Pct"] > benchmark])
    below_bench = len(df[df["ROI_Pct"] <= benchmark])

    if alpha > 0:
        status    = "good"
        delta_txt = f"+{alpha:.2f}% above Nifty 50"
    elif alpha > -3:
        status    = "warning"
        delta_txt = f"{alpha:.2f}% vs Nifty 50"
    else:
        status    = "danger"
        delta_txt = f"{alpha:.2f}% below Nifty 50"

    return {
        "label"   : "Average ROI",
        "icon"    : "📈",
        "value"   : f"{avg_roi:.2f}%",
        "delta"   : delta_txt,
        "status"  : status,
        "detail"  : f"{above_bench} clients beat benchmark · {below_bench} below",
        "raw"     : avg_roi,
        "delta_direction": "up" if alpha >= 0 else "down",
    }


def _kpi_high_risk_clients(df: pd.DataFrame) -> dict:
    """
    KPI 3 — HIGH RISK CLIENTS
    ──────────────────────────
    WHAT IT IS:
        Count of clients with Risk_Score ≥ 7.
        Risk Score 7–10 = "High" to "Very High" on our scale.

    WHY IT MATTERS:
        High-risk clients are both an opportunity and a liability.
        They can generate excellent returns but are most likely to
        exit during a market downturn. Advisors need to monitor
        them proactively — especially those with conservative goals
        (Retirement, Emergency Fund) who shouldn't be in high-risk.

    CALCULATION:
        high_risk_clients = COUNT WHERE Risk_Score >= 7
        high_risk_pct     = high_risk_clients / total_clients * 100
        aum_at_risk       = SUM(Portfolio_Value_INR) WHERE Risk_Score >= 7

    BUSINESS RULE:
        > 40% clients high risk → danger  (firm-level concentration risk)
        20–40%                  → warning
        < 20%                   → good
    """
    high_risk       = df[df["Risk_Score"] >= 7]
    count           = len(high_risk)
    pct             = count / len(df) * 100 if len(df) > 0 else 0
    aum_at_risk_cr  = high_risk["Portfolio_Value_INR"].sum() / 1e7

    # Among high-risk clients, how many have conservative goals?
    misaligned = len(high_risk[
        high_risk["Financial_Goal"].isin(["Retirement Planning", "Emergency Fund"])
    ])

    if pct > 40:
        status = "danger"
    elif pct > 20:
        status = "warning"
    else:
        status = "good"

    return {
        "label"   : "High Risk Clients",
        "icon"    : "⚠️",
        "value"   : f"{count}",
        "delta"   : f"{pct:.1f}% of total · ₹{aum_at_risk_cr:.1f} Cr at risk",
        "status"  : status,
        "detail"  : f"{misaligned} misaligned with conservative goals",
        "raw"     : count,
        "delta_direction": "down" if pct > 20 else "neutral",
    }


def _kpi_best_sector(df: pd.DataFrame) -> dict:
    """
    KPI 4 — BEST PERFORMING SECTOR
    ────────────────────────────────
    WHAT IT IS:
        The sector (Technology, Banking, FMCG, etc.) with the
        highest average ROI across all clients invested in it.

    WHY IT MATTERS:
        Advisors use this to identify where to concentrate new
        investments. If FMCG is consistently outperforming, new
        clients should be steered toward FMCG-heavy instruments.
        The gap between best and worst sectors also shows how
        much diversification benefit is being left on the table.

    CALCULATION:
        sector_avg_roi = GROUPBY(Sector) → MEAN(ROI_Pct)
        best_sector    = sector with MAX avg ROI
        sector_spread  = best_roi - worst_roi  (diversification value)

    BUSINESS RULE:
        Always "good" for display — this is a positive insight.
        But if spread > 20% → alert to diversify into top sectors.
    """
    sector_roi  = df.groupby("Sector")["ROI_Pct"].mean().sort_values(ascending=False)
    best_name   = sector_roi.idxmax()
    best_roi    = sector_roi.max()
    worst_roi   = sector_roi.min()
    spread      = best_roi - worst_roi

    # How many clients are invested in the best sector?
    clients_in_best = len(df[df["Sector"] == best_name])

    return {
        "label"   : "Best Performing Sector",
        "icon"    : "🏆",
        "value"   : best_name,
        "delta"   : f"{best_roi:.1f}% avg ROI · {spread:.1f}% spread",
        "status"  : "good",
        "detail"  : f"{clients_in_best} clients · vs worst sector {worst_roi:.1f}%",
        "raw"     : best_roi,
        "delta_direction": "up",
    }


def _kpi_avg_monthly_return(df: pd.DataFrame) -> dict:
    """
    KPI 5 — AVERAGE MONTHLY RETURN
    ────────────────────────────────
    WHAT IT IS:
        Mean of Monthly_Return_Pct across all filtered clients.
        This is the percentage gain or loss in the most recent month.

    WHY IT MATTERS:
        While ROI is the long-term picture, monthly return is the
        SHORT-TERM pulse. A client who sees a negative monthly
        return is a churn risk even if their annual ROI is fine.
        Advisors use this to proactively call clients before they
        call to complain.

    CALCULATION:
        avg_monthly      = MEAN(Monthly_Return_Pct)
        annualised_equiv = avg_monthly * 12  (simple approximation)
        positive_clients = COUNT WHERE Monthly_Return_Pct > 0

    BUSINESS RULE:
        avg_monthly > 1.0%  → good  (above ~12% annualised)
        0 < avg ≤ 1.0%      → warning  (below benchmark pace)
        avg ≤ 0             → danger  (portfolio losing money)
    """
    avg_monthly   = df["Monthly_Return_Pct"].mean()
    ann_equiv     = avg_monthly * 12
    positive      = len(df[df["Monthly_Return_Pct"] > 0])
    negative      = len(df[df["Monthly_Return_Pct"] <= 0])
    best_type_sr  = df.groupby("Investment_Type")["Monthly_Return_Pct"].mean()
    best_type     = best_type_sr.idxmax()

    if avg_monthly > 1.0:
        status = "good"
    elif avg_monthly > 0:
        status = "warning"
    else:
        status = "danger"

    return {
        "label"   : "Avg Monthly Return",
        "icon"    : "📅",
        "value"   : f"{avg_monthly:.2f}%",
        "delta"   : f"≈ {ann_equiv:.1f}% annualised",
        "status"  : status,
        "detail"  : f"{positive} growing · {negative} declining · Best: {best_type}",
        "raw"     : avg_monthly,
        "delta_direction": "up" if avg_monthly > 0 else "down",
    }


def compute_kpis(df: pd.DataFrame) -> list[dict]:
    """
    Master function — computes all 5 KPIs in order.
    Returns a list of dicts, one per card.

    Call this ONCE per filter change (Streamlit re-runs handle that).
    Each dict is passed directly to render_kpi_row().
    """
    return [
        _kpi_total_portfolio(df),
        _kpi_average_roi(df),
        _kpi_high_risk_clients(df),
        _kpi_best_sector(df),
        _kpi_avg_monthly_return(df),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — CSS INJECTION
# Injects the card styles. Called once at app startup.
# ══════════════════════════════════════════════════════════════════════════════

_STATUS_COLORS = {
    "good"    : ("#2ECC71", "#E9FAF1"),   # (border, bg-tint)
    "warning" : ("#F39C12", "#FEF6E7"),
    "danger"  : ("#E74C3C", "#FDEDEC"),
    "neutral" : ("#1E6FBA", "#EAF2FB"),
}

_DELTA_ARROWS = {
    "up"      : ("▲", "#2ECC71"),
    "down"    : ("▼", "#E74C3C"),
    "neutral" : ("●", "#7F8C8D"),
}


def inject_kpi_css():
    """
    Inject the CSS for KPI cards into the Streamlit page.
    Must be called before render_kpi_row().
    Typically called once near the top of app.py.
    """
    st.markdown("""
    <style>
    /* ── KPI card wrapper ──────────────────────────────────────── */
    .kpi-card {
        background     : #FFFFFF;
        border-radius  : 14px;
        padding        : 20px 22px 16px 22px;
        border         : 1px solid #E8ECF0;
        box-shadow     : 0 2px 10px rgba(10,35,66,0.06);
        transition     : transform 0.18s ease, box-shadow 0.18s ease;
        position       : relative;
        overflow       : hidden;
        min-height     : 148px;
    }
    .kpi-card:hover {
        transform      : translateY(-3px);
        box-shadow     : 0 8px 24px rgba(10,35,66,0.13);
    }

    /* Coloured left accent bar (4px wide strip on left edge) */
    .kpi-card::before {
        content        : '';
        position       : absolute;
        left           : 0; top : 0; bottom : 0;
        width          : 4px;
        border-radius  : 14px 0 0 14px;
    }
    .kpi-good::before    { background: #2ECC71; }
    .kpi-warning::before { background: #F39C12; }
    .kpi-danger::before  { background: #E74C3C; }
    .kpi-neutral::before { background: #1E6FBA; }

    /* Faint tint behind the whole card */
    .kpi-good    { background: linear-gradient(135deg, #FFFFFF 60%, #F0FBF5 100%); }
    .kpi-warning { background: linear-gradient(135deg, #FFFFFF 60%, #FEFAF0 100%); }
    .kpi-danger  { background: linear-gradient(135deg, #FFFFFF 60%, #FDF3F2 100%); }
    .kpi-neutral { background: linear-gradient(135deg, #FFFFFF 60%, #EFF5FC 100%); }

    /* Icon badge — top-right corner */
    .kpi-icon {
        position    : absolute;
        top         : 16px;
        right       : 18px;
        font-size   : 24px;
        opacity     : 0.55;
        line-height : 1;
    }

    /* Label (small caps above the value) */
    .kpi-label {
        font-size      : 11px;
        font-weight    : 700;
        color          : #6B7280;
        text-transform : uppercase;
        letter-spacing : 0.7px;
        margin-bottom  : 8px;
        padding-right  : 34px;  /* clear the icon */
    }

    /* Main value — the big number */
    .kpi-value {
        font-size   : 28px;
        font-weight : 800;
        color       : #0A2342;
        line-height : 1.1;
        margin-bottom: 7px;
        letter-spacing: -0.5px;
    }

    /* Delta — comparison line */
    .kpi-delta {
        font-size   : 12px;
        color       : #6B7280;
        display     : flex;
        align-items : center;
        gap         : 5px;
        margin-bottom: 10px;
    }
    .kpi-delta .arrow-up   { color: #2ECC71; font-size: 11px; }
    .kpi-delta .arrow-down { color: #E74C3C; font-size: 11px; }
    .kpi-delta .arrow-flat { color: #7F8C8D; font-size: 11px; }

    /* Divider line */
    .kpi-divider {
        height          : 1px;
        background      : #E8ECF0;
        margin          : 0 -4px 9px -4px;
    }

    /* Detail — small context line at the bottom */
    .kpi-detail {
        font-size   : 11px;
        color       : #9CA3AF;
        line-height : 1.5;
        white-space : nowrap;
        overflow    : hidden;
        text-overflow: ellipsis;
    }

    /* Remove Streamlit's default column gap for KPI row */
    div[data-testid="column"] > div:first-child {
        padding-left  : 4px;
        padding-right : 4px;
    }
    </style>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — RENDER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _card_html(kpi: dict) -> str:
    """
    Builds the HTML string for a single KPI card.
    Called by render_kpi_row() for each of the 5 KPIs.

    Parameters
    ----------
    kpi : dict   The dict returned by one of the _kpi_*() functions.

    Returns
    -------
    str          Raw HTML to pass into st.markdown(unsafe_allow_html=True).
    """
    status    = kpi.get("status", "neutral")
    direction = kpi.get("delta_direction", "neutral")

    # Arrow symbol and colour based on direction
    arrow_map = {
        "up"     : ('<span class="arrow-up">▲</span>',   ""),
        "down"   : ('<span class="arrow-down">▼</span>', ""),
        "neutral": ('<span class="arrow-flat">●</span>', ""),
    }
    arrow_html = arrow_map.get(direction, arrow_map["neutral"])[0]

    return f"""
    <div class="kpi-card kpi-{status}">
        <div class="kpi-icon">{kpi['icon']}</div>
        <div class="kpi-label">{kpi['label']}</div>
        <div class="kpi-value">{kpi['value']}</div>
        <div class="kpi-delta">{arrow_html} {kpi['delta']}</div>
        <div class="kpi-divider"></div>
        <div class="kpi-detail">📌 {kpi['detail']}</div>
    </div>
    """


def render_kpi_row(kpis: list[dict]):
    """
    Renders all 5 KPI cards in a single horizontal row.

    Layout: uses st.columns(5) to place one card per column.
    Each column renders one card via st.markdown(html, unsafe_allow_html=True).

    Parameters
    ----------
    kpis : list[dict]   Output of compute_kpis(df) — list of 5 dicts.

    Usage in app.py:
    ----------------
        kpis = compute_kpis(df)
        render_kpi_row(kpis)
    """
    # Make sure CSS is injected
    inject_kpi_css()

    # Section header
    

    # 5 equal columns — one card each
    cols = st.columns(5, gap="small")

    for col, kpi in zip(cols, kpis):
        with col:
            st.markdown(_card_html(kpi), unsafe_allow_html=True)

    # Summary bar below the cards
    _render_summary_bar(kpis)


def _render_summary_bar(kpis: list[dict]):
    """
    Renders a slim status bar directly below the KPI cards.
    Shows how many KPIs are in good / warning / danger state —
    giving the advisor an instant portfolio health score.
    """
    counts = {"good": 0, "warning": 0, "danger": 0, "neutral": 0}
    for k in kpis:
        counts[k.get("status", "neutral")] += 1

    total  = len(kpis)
    good_w = round(counts["good"]    / total * 100)
    warn_w = round(counts["warning"] / total * 100)
    dang_w = round(counts["danger"]  / total * 100)
    neut_w = 100 - good_w - warn_w - dang_w

    health_labels = {0: "Critical", 1: "Poor", 2: "Fair", 3: "Good", 4: "Strong", 5: "Excellent"}
    health_score  = counts["good"] + counts["neutral"] // 2
    health_label  = health_labels.get(health_score, "Good")
    health_color  = "#2ECC71" if health_score >= 4 else "#F39C12" if health_score >= 2 else "#E74C3C"

    st.markdown(f"""
    <div style="margin-top:10px; display:flex; align-items:center; gap:16px;">
        <div style="font-size:11px; color:#6B7280; font-weight:600;
                    text-transform:uppercase; letter-spacing:0.5px; flex-shrink:0;">
            Portfolio Health
        </div>
        <div style="flex:1; height:6px; background:#F0F2F4;
                    border-radius:3px; overflow:hidden; display:flex;">
            <div style="width:{good_w}%; background:#2ECC71;"></div>
            <div style="width:{warn_w}%; background:#F39C12;"></div>
            <div style="width:{dang_w}%; background:#E74C3C;"></div>
            <div style="width:{neut_w}%; background:#1E6FBA; opacity:0.4;"></div>
        </div>
        <div style="font-size:12px; font-weight:700; color:{health_color}; flex-shrink:0;">
            {health_label}
        </div>
        <div style="font-size:11px; color:#9CA3AF; flex-shrink:0;">
            {counts['good']}✓ &nbsp; {counts['warning']}⚠ &nbsp; {counts['danger']}✗
        </div>
    </div>
    <div style="margin-bottom:8px;"></div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PART 4 — STANDALONE TEST (run this file directly to see output)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Quick sanity check — run with:  python utils/kpi_cards.py
    Prints all computed KPI values to the terminal without needing Streamlit.
    """
    import sys
    from unittest.mock import MagicMock
    sys.modules.setdefault("streamlit", MagicMock())

    df = pd.read_csv("data/win_advisors_portfolio_dataset.csv")
    df["Risk_Score"]          = df["Risk_Score"].astype(int)
    df["ROI_Pct"]             = df["ROI_Pct"].round(2)
    df["Portfolio_Value_INR"] = df["Portfolio_Value_INR"].astype(int)

    kpis = compute_kpis(df)

    print("\n" + "═" * 60)
    print("  WIN ADVISORS — KPI Validation")
    print("═" * 60)
    for i, k in enumerate(kpis, 1):
        status_icon = {"good": "✅", "warning": "⚠️", "danger": "🔴", "neutral": "ℹ️"}
        si = status_icon.get(k["status"], "•")
        print(f"\n  KPI {i} — {k['icon']} {k['label']}")
        print(f"    Value   : {k['value']}")
        print(f"    Delta   : {k['delta']}")
        print(f"    Status  : {si} {k['status'].upper()}")
        print(f"    Detail  : {k['detail']}")
    print("\n" + "═" * 60 + "\n")