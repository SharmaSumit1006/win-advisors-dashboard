"""
utils/recommendation_engine.py
================================
AI-style portfolio recommendation engine for WIN Advisors Dashboard.

WHAT THIS MODULE DOES
──────────────────────
Scans the filtered DataFrame for 10 distinct portfolio conditions and
produces a list of Recommendation objects — each with a severity level,
title, business explanation, suggested action, and supporting metrics.

The recommendations are purely rule-based (no ML/AI library needed).
They are called "AI-style" because they automatically surface insights
that would otherwise require an analyst to manually inspect the data.
Every insight re-calculates when the sidebar filters change.

HOW TO USE IN app.py  (2 steps)
────────────────────────────────
  STEP 1 — Import:
    from utils.recommendation_engine import generate_recommendations, render_recommendations

  STEP 2 — Render (after your charts section):
    recommendations = generate_recommendations(df)
    render_recommendations(recommendations)

  That's it. Pass the FILTERED df so insights react to sidebar filters.

RECOMMENDATION SEVERITY LEVELS
────────────────────────────────
  CRITICAL  → red    — immediate action required, significant risk/loss
  WARNING   → amber  — attention needed, monitor closely
  POSITIVE  → green  — opportunity or strength to act on

THE 10 INSIGHT RULES
─────────────────────
  1.  Risk Misalignment        — high-risk clients with conservative goals
  2.  Underperforming Sectors  — sectors below the 12% benchmark
  3.  Best Sector Opportunity  — top-ROI sector that is under-allocated
  4.  AUM Concentration        — single investment type > 30% of book
  5.  Underperforming Types    — asset classes consistently below benchmark
  6.  HNI Client Opportunity   — high-value clients for premium service
  7.  Top Performer Benchmark  — replicate winning strategies
  8.  Over-Conservative Risk   — very-low-risk clients earning sub-inflation
  9.  Poor Risk-Adjusted Return — clients taking risk without proportional reward
  10. Sector Concentration Risk — two correlated sectors dominating AUM
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
BENCHMARK_ROI      = 12.0   # Nifty 50 long-run annual return (%)
INFLATION_RATE     = 6.0    # Approximate Indian CPI inflation (%)
HNI_THRESHOLD_L    = 100.0  # High Net-worth Individual: ₹100 Lakhs+
CONCENTRATION_PCT  = 30.0   # Single type > 30% = concentration risk
RISK_ADJ_MIN       = 2.0    # Minimum acceptable risk-adjusted return ratio
HIGH_RISK_SCORE    = 7      # Risk_Score >= this = High / Very High


# ─────────────────────────────────────────────────────────────────────────────
#  DATA CLASS — one recommendation card
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Recommendation:
    """
    A single recommendation card.

    Fields
    ──────
    severity    : "CRITICAL" | "WARNING" | "POSITIVE"
                  Controls card colour: red | amber | green
    category    : Short category label shown as a badge
    title       : Headline — one clear sentence
    explanation : 2–3 sentences explaining the business problem/opportunity
    action      : A specific, concrete step the advisor should take
    metrics     : dict of supporting numbers shown below the card text
                  e.g. {"Affected clients": 10, "AUM at risk": "₹3.2 Cr"}
    priority    : int 1–10, lower = shown first (1 = most urgent)
    icon        : Emoji shown in the card header
    affected_ids: Optional list of Client_IDs for drill-down (future use)
    """
    severity    : str
    category    : str
    title       : str
    explanation : str
    action      : str
    metrics     : dict          = field(default_factory=dict)
    priority    : int           = 5
    icon        : str           = "💡"
    affected_ids: list[str]     = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def _fmt_cr(rupees: float) -> str:
    """Formats raw rupee value to ₹X.XX Cr string."""
    return f"₹{rupees / 1e7:.2f} Cr"

def _fmt_l(rupees: float) -> str:
    """Formats raw rupee value to ₹X.X L string."""
    return f"₹{rupees / 1e5:.1f}L"

def _fmt_pct(value: float) -> str:
    """Formats float to percentage string."""
    return f"{value:.1f}%"


# ─────────────────────────────────────────────────────────────────────────────
#  RULE 1 — Risk Misalignment
# ─────────────────────────────────────────────────────────────────────────────
def _rule_risk_misalignment(df: pd.DataFrame) -> Optional[Recommendation]:
    """
    WHAT IT DETECTS
    ───────────────
    Clients whose Risk_Score is HIGH (≥7) but whose Financial_Goal
    is CONSERVATIVE (Retirement Planning or Emergency Fund).

    WHY IT MATTERS
    ──────────────
    A 60-year-old planning retirement should NOT have 80% in equities.
    If markets drop 30%, their savings shrink just before they need them.
    This is both a financial risk AND a regulatory/compliance risk for
    the advisory firm.

    SEVERITY: CRITICAL — requires immediate advisory intervention.
    """
    conservative_goals = ["Retirement Planning", "Emergency Fund"]
    misaligned = df[
        (df["Risk_Score"] >= HIGH_RISK_SCORE) &
        (df["Financial_Goal"].isin(conservative_goals))
    ]
    if misaligned.empty:
        return None

    aum_at_risk = misaligned["Portfolio_Value_INR"].sum()
    avg_risk    = misaligned["Risk_Score"].mean()
    goals_breakdown = misaligned["Financial_Goal"].value_counts().to_dict()
    goal_str = ", ".join(f'{v} {k}' for k, v in goals_breakdown.items())

    return Recommendation(
        severity    = "CRITICAL",
        category    = "Risk Compliance",
        icon        = "🚨",
        priority    = 1,
        title       = f"{len(misaligned)} Clients Have Misaligned Risk Profiles",
        explanation = (
            f"{len(misaligned)} client(s) ({goal_str}) hold portfolios with an "
            f"average Risk Score of {avg_risk:.1f}/10 — classified as High or Very High. "
            f"These clients are exposed to significant market volatility that is "
            f"incompatible with their stated financial goals. "
            f"A 20% market correction would directly impact {_fmt_cr(aum_at_risk)} of AUM."
        ),
        action = (
            "Schedule immediate rebalancing consultations. Shift 30–40% of high-risk "
            "instruments (Equity, Crypto) into Capital Protection Funds, Government "
            "Bonds, or Fixed Deposits. Target Risk Score ≤ 4 for Retirement clients."
        ),
        metrics = {
            "Misaligned clients" : len(misaligned),
            "AUM at risk"        : _fmt_cr(aum_at_risk),
            "Avg Risk Score"     : f"{avg_risk:.1f}/10",
            "Goals affected"     : goal_str,
        },
        affected_ids = misaligned["Client_ID"].tolist(),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RULE 2 — Underperforming Sectors
# ─────────────────────────────────────────────────────────────────────────────
def _rule_underperforming_sectors(df: pd.DataFrame) -> Optional[Recommendation]:
    """
    WHAT IT DETECTS
    ───────────────
    Sectors where the average client ROI is BELOW the 12% benchmark.
    These sectors are generating sub-market returns for clients invested in them.

    SEVERITY: WARNING — not an emergency but needs strategic attention.
    """
    sector_roi = df.groupby("Sector")["ROI_Pct"].agg(
        mean="mean", count="count"
    )
    underperformers = sector_roi[sector_roi["mean"] < BENCHMARK_ROI].sort_values("mean")

    if underperformers.empty:
        return None

    # Clients trapped in underperforming sectors
    affected_clients = df[df["Sector"].isin(underperformers.index)]
    trapped_aum      = affected_clients["Portfolio_Value_INR"].sum()

    worst_sector     = underperformers.index[0]
    worst_roi        = underperformers.loc[worst_sector, "mean"]

    sector_detail = " | ".join(
        f'{s}: {r["mean"]:.1f}%' for s, r in underperformers.iterrows()
    )

    return Recommendation(
        severity    = "WARNING",
        category    = "Sector Performance",
        icon        = "📉",
        priority    = 3,
        title       = f"{len(underperformers)} Sectors Underperforming the {BENCHMARK_ROI}% Benchmark",
        explanation = (
            f"The following sectors are delivering below-benchmark returns: {sector_detail}. "
            f"The worst performer is {worst_sector} at {worst_roi:.1f}% — "
            f"{BENCHMARK_ROI - worst_roi:.1f} percentage points below the Nifty 50. "
            f"{len(affected_clients)} client(s) with {_fmt_cr(trapped_aum)} are "
            f"concentrated in these underperforming sectors."
        ),
        action = (
            f"Review portfolio allocations for the {len(affected_clients)} affected clients. "
            f"Consider gradual reallocation toward FMCG, Consumer Goods, or Technology "
            f"which show stronger returns in the current filtered view. "
            f"Use a 3–6 month staggered exit to minimise market impact."
        ),
        metrics = {
            "Underperforming sectors" : len(underperformers),
            "Worst sector"            : f"{worst_sector} ({worst_roi:.1f}%)",
            "Affected clients"        : len(affected_clients),
            "Trapped AUM"             : _fmt_cr(trapped_aum),
            "Benchmark gap"           : f"{BENCHMARK_ROI - worst_roi:.1f}%",
        },
        affected_ids = affected_clients["Client_ID"].tolist(),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RULE 3 — Best Sector Opportunity
# ─────────────────────────────────────────────────────────────────────────────
def _rule_best_sector_opportunity(df: pd.DataFrame) -> Optional[Recommendation]:
    """
    WHAT IT DETECTS
    ───────────────
    The top-performing sector by average ROI where the firm is
    UNDER-ALLOCATED (fewer clients than its performance warrants).
    Threshold: top sector holds < 10% of total clients.

    SEVERITY: POSITIVE — opportunity to grow.
    """
    sector_stats = df.groupby("Sector").agg(
        avg_roi  = ("ROI_Pct",             "mean"),
        n_clients= ("Client_ID",           "count"),
        aum      = ("Portfolio_Value_INR", "sum"),
    )
    best_sector = sector_stats["avg_roi"].idxmax()
    best_roi    = sector_stats.loc[best_sector, "avg_roi"]
    best_clients= sector_stats.loc[best_sector, "n_clients"]
    best_aum    = sector_stats.loc[best_sector, "aum"]
    client_pct  = best_clients / len(df) * 100

    # Only fire if under-allocated (< 10% of clients)
    if client_pct >= 10:
        return None

    opportunity_aum = df["Portfolio_Value_INR"].sum() * 0.05  # 5% realloc estimate

    return Recommendation(
        severity    = "POSITIVE",
        category    = "Growth Opportunity",
        icon        = "🏆",
        priority    = 4,
        title       = f"{best_sector} Is the Top Sector at {best_roi:.1f}% ROI — Only {client_pct:.0f}% of Clients Are Invested",
        explanation = (
            f"{best_sector} leads all sectors with an average ROI of {best_roi:.1f}%, "
            f"significantly outperforming the {BENCHMARK_ROI}% benchmark. "
            f"Yet only {best_clients} client(s) ({client_pct:.1f}% of the book) "
            f"are currently allocated here, representing {_fmt_cr(best_aum)} of AUM. "
            f"This sector is substantially under-represented relative to its performance."
        ),
        action = (
            f"Identify clients in low-performing sectors (Automotive, Infrastructure) "
            f"and propose a {best_sector}-focused instrument. Even reallocating 5% of "
            f"total AUM (~{_fmt_cr(opportunity_aum)}) could meaningfully improve "
            f"portfolio-wide returns. Prepare a client-ready sector performance report."
        ),
        metrics = {
            "Best sector ROI"  : _fmt_pct(best_roi),
            "Clients invested" : f"{best_clients} ({client_pct:.1f}%)",
            "Current sector AUM": _fmt_cr(best_aum),
            "Potential realloc" : _fmt_cr(opportunity_aum),
            "vs Benchmark"      : f"+{best_roi - BENCHMARK_ROI:.1f}%",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RULE 4 — AUM Concentration by Investment Type
# ─────────────────────────────────────────────────────────────────────────────
def _rule_aum_concentration(df: pd.DataFrame) -> Optional[Recommendation]:
    """
    WHAT IT DETECTS
    ───────────────
    Any single investment type that holds more than CONCENTRATION_PCT (30%)
    of the firm's total AUM. Single-instrument concentration is a systemic risk.

    SEVERITY: WARNING if one type > 30%, CRITICAL if > 50%.
    """
    type_aum = df.groupby("Investment_Type")["Portfolio_Value_INR"].sum()
    type_pct = (type_aum / type_aum.sum() * 100).sort_values(ascending=False)
    concentrated = type_pct[type_pct > CONCENTRATION_PCT]

    if concentrated.empty:
        return None

    top_type     = concentrated.index[0]
    top_pct      = concentrated.iloc[0]
    top_aum      = type_aum[top_type]
    severity     = "CRITICAL" if top_pct > 50 else "WARNING"
    n_clients    = df[df["Investment_Type"] == top_type].shape[0]

    return Recommendation(
        severity    = severity,
        category    = "Concentration Risk",
        icon        = "⚠️" if severity == "WARNING" else "🚨",
        priority    = 2 if severity == "CRITICAL" else 4,
        title       = f"{top_type} Holds {top_pct:.1f}% of Total AUM — Concentration Risk Detected",
        explanation = (
            f"{top_type} accounts for {top_pct:.1f}% of total AUM ({_fmt_cr(top_aum)}) "
            f"across {n_clients} clients. The recommended maximum for any single "
            f"instrument type is {CONCENTRATION_PCT:.0f}% to ensure diversification. "
            f"Overexposure means a sector-specific shock (regulatory change, market crash) "
            f"could impact a disproportionate share of the firm's revenue and client value."
        ),
        action = (
            f"Set a firm-level policy: no single instrument type should exceed "
            f"{CONCENTRATION_PCT:.0f}% of book AUM. For new client onboarding, steer "
            f"toward under-represented types (Gold, Real Estate, ETFs). "
            f"For existing clients, offer diversification consultations with a "
            f"target of reducing {top_type} exposure to below 25% over 6 months."
        ),
        metrics = {
            "Concentrated type"  : top_type,
            "Concentration level": _fmt_pct(top_pct),
            "AUM concentrated"   : _fmt_cr(top_aum),
            "Clients exposed"    : n_clients,
            "Safe threshold"     : f"{CONCENTRATION_PCT:.0f}%",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RULE 5 — Underperforming Investment Types
# ─────────────────────────────────────────────────────────────────────────────
def _rule_underperforming_types(df: pd.DataFrame) -> Optional[Recommendation]:
    """
    WHAT IT DETECTS
    ───────────────
    Investment types where average ROI is below BENCHMARK_ROI (12%).
    Unlike Rule 2 (sectors), this looks at the instrument level.

    SEVERITY: WARNING — sub-benchmark instruments that hold significant AUM.
    """
    type_stats = df.groupby("Investment_Type").agg(
        avg_roi  = ("ROI_Pct",             "mean"),
        n_clients= ("Client_ID",           "count"),
        aum      = ("Portfolio_Value_INR", "sum"),
    )
    underperformers = type_stats[type_stats["avg_roi"] < BENCHMARK_ROI].sort_values("avg_roi")

    if underperformers.empty:
        return None

    # Filter to only types with meaningful AUM (> 2% of total)
    total_aum = df["Portfolio_Value_INR"].sum()
    significant = underperformers[
        (underperformers["aum"] / total_aum) > 0.02
    ]

    if significant.empty:
        return None

    total_trapped_aum = significant["aum"].sum()
    worst_type        = significant["avg_roi"].idxmin()
    worst_roi         = significant.loc[worst_type, "avg_roi"]

    type_detail = " | ".join(
        f'{t}: {r["avg_roi"]:.1f}% (n={int(r["n_clients"])})'
        for t, r in significant.iterrows()
    )

    return Recommendation(
        severity    = "WARNING",
        category    = "Instrument Performance",
        icon        = "📊",
        priority    = 5,
        title       = f"{len(significant)} Investment Types Earning Below the {BENCHMARK_ROI}% Benchmark",
        explanation = (
            f"The following investment types are delivering sub-benchmark returns: "
            f"{type_detail}. "
            f"These instruments collectively hold {_fmt_cr(total_trapped_aum)} of AUM. "
            f"With inflation at ~{INFLATION_RATE}%, some of these ({worst_type} at "
            f"{worst_roi:.1f}%) are barely preserving real purchasing power."
        ),
        action = (
            f"For Fixed Deposit and Bonds clients, explore higher-yield alternatives: "
            f"Corporate Bond Funds (10–12%), Balanced Advantage Funds, or Debt ETFs. "
            f"Ensure clients understand that moving from FD to market instruments "
            f"introduces volatility — match the upgrade to their risk tolerance."
        ),
        metrics = {
            "Sub-benchmark types"     : len(significant),
            "Worst type"              : f"{worst_type} ({worst_roi:.1f}%)",
            "AUM in sub-benchmark"    : _fmt_cr(total_trapped_aum),
            "Benchmark gap (worst)"   : f"{BENCHMARK_ROI - worst_roi:.1f}%",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RULE 6 — HNI Client Opportunity
# ─────────────────────────────────────────────────────────────────────────────
def _rule_hni_opportunity(df: pd.DataFrame) -> Optional[Recommendation]:
    """
    WHAT IT DETECTS
    ───────────────
    Clients with Portfolio_Value_L >= HNI_THRESHOLD_L (₹100 Lakhs).
    These clients represent disproportionate AUM contribution and deserve
    premium service attention.

    SEVERITY: POSITIVE — revenue and retention opportunity.
    """
    hni = df[df["Portfolio_Value_L"] >= HNI_THRESHOLD_L]
    if hni.empty:
        return None

    hni_aum     = hni["Portfolio_Value_INR"].sum()
    total_aum   = df["Portfolio_Value_INR"].sum()
    hni_pct     = hni_aum / total_aum * 100
    avg_hni_roi = hni["ROI_Pct"].mean()
    fee_estimate= hni_aum * 0.01   # 1% advisory fee estimate

    return Recommendation(
        severity    = "POSITIVE",
        category    = "HNI Management",
        icon        = "💎",
        priority    = 6,
        title       = f"{len(hni)} HNI Clients Hold {hni_pct:.1f}% of Total AUM — Premium Tier Opportunity",
        explanation = (
            f"{len(hni)} High Net-worth client(s) each hold portfolios exceeding "
            f"₹{HNI_THRESHOLD_L:.0f}L, collectively representing {_fmt_cr(hni_aum)} "
            f"({hni_pct:.1f}% of total AUM). Their average ROI is {avg_hni_roi:.1f}%. "
            f"At a 1% advisory fee, these clients alone represent ~{_fmt_cr(fee_estimate)} "
            f"in annual fee revenue. Retaining them is the single highest-ROI activity "
            f"for the firm."
        ),
        action = (
            f"Create a dedicated HNI service tier with quarterly face-to-face reviews, "
            f"customised portfolio reports, and priority access to new investment products. "
            f"Assign a dedicated relationship manager to each HNI client. "
            f"Consider Family Office services for clients above ₹200L."
        ),
        metrics = {
            "HNI clients"       : len(hni),
            "HNI total AUM"     : _fmt_cr(hni_aum),
            "% of book"         : _fmt_pct(hni_pct),
            "Avg HNI ROI"       : _fmt_pct(avg_hni_roi),
            "Est. annual fees"  : _fmt_cr(fee_estimate),
        },
        affected_ids = hni["Client_ID"].tolist(),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RULE 7 — Top Performer Replication
# ─────────────────────────────────────────────────────────────────────────────
def _rule_top_performers(df: pd.DataFrame) -> Optional[Recommendation]:
    """
    WHAT IT DETECTS
    ───────────────
    Clients with ROI >= 20% — high performers whose strategies can be
    analysed and replicated for similar-profile clients.

    SEVERITY: POSITIVE — strategy intelligence.
    """
    top = df[df["ROI_Pct"] >= 20.0]
    if len(top) < 3:
        return None

    avg_roi      = top["ROI_Pct"].mean()
    avg_risk     = top["Risk_Score"].mean()
    top_types    = top["Investment_Type"].value_counts()
    top_sectors  = top["Sector"].value_counts()
    dominant_type   = top_types.index[0]
    dominant_sector = top_sectors.index[0]

    return Recommendation(
        severity    = "POSITIVE",
        category    = "Strategy Intelligence",
        icon        = "⭐",
        priority    = 7,
        title       = f"{len(top)} Clients Achieving {avg_roi:.1f}% Avg ROI — Replicate Their Strategy",
        explanation = (
            f"{len(top)} client(s) are delivering outstanding returns averaging "
            f"{avg_roi:.1f}% with an average Risk Score of {avg_risk:.1f}/10. "
            f"Their portfolios are most concentrated in {dominant_type} "
            f"({top_types.iloc[0]} clients) and the {dominant_sector} sector "
            f"({top_sectors.iloc[0]} clients). This suggests a winning combination "
            f"that can be systematically applied to similar-profile clients."
        ),
        action = (
            f"Analyse the top {min(5, len(top))} performers in detail. Document their "
            f"asset allocation, sector exposure, and investment duration. Build a "
            f"'Model Portfolio' template based on their commonalities and present it "
            f"to new clients with a similar risk profile ({avg_risk:.0f}/10) and goal."
        ),
        metrics = {
            "Top performers"        : len(top),
            "Avg ROI"               : _fmt_pct(avg_roi),
            "Avg Risk Score"        : f"{avg_risk:.1f}/10",
            "Dominant type"         : dominant_type,
            "Dominant sector"       : dominant_sector,
        },
        affected_ids = top["Client_ID"].tolist(),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RULE 8 — Over-Conservative Clients
# ─────────────────────────────────────────────────────────────────────────────
def _rule_over_conservative(df: pd.DataFrame) -> Optional[Recommendation]:
    """
    WHAT IT DETECTS
    ───────────────
    Clients with Risk_Score <= 2 AND ROI < 8% (barely above inflation).
    These clients are playing it too safe at the cost of real returns.

    SEVERITY: WARNING — long-term wealth erosion risk.
    """
    over_cons = df[(df["Risk_Score"] <= 2) & (df["ROI_Pct"] < 8.0)]
    if over_cons.empty:
        return None

    avg_roi     = over_cons["ROI_Pct"].mean()
    total_aum   = over_cons["Portfolio_Value_INR"].sum()
    real_return = avg_roi - INFLATION_RATE  # approx real return after inflation
    types_used  = over_cons["Investment_Type"].value_counts().index[:2].tolist()

    return Recommendation(
        severity    = "WARNING",
        category    = "Return Optimisation",
        icon        = "🐢",
        priority    = 8,
        title       = f"{len(over_cons)} Clients Too Conservative — Real Returns Near Zero",
        explanation = (
            f"{len(over_cons)} client(s) have a Risk Score of 1–2 and an average "
            f"annual ROI of {avg_roi:.1f}%. With inflation at ~{INFLATION_RATE}%, "
            f"their real (inflation-adjusted) return is approximately "
            f"{real_return:+.1f}% — meaning their purchasing power is barely growing. "
            f"Most are concentrated in {' and '.join(types_used)}."
        ),
        action = (
            f"Propose a gradual 'step-up' plan: introduce 10–15% allocation to "
            f"Balanced Mutual Funds or Short-Duration Debt Funds. This can improve "
            f"returns to 10–11% with minimal additional risk. Frame it as "
            f"'inflation protection' rather than 'risk-taking' in client conversations."
        ),
        metrics = {
            "Over-conservative clients" : len(over_cons),
            "Avg ROI"                   : _fmt_pct(avg_roi),
            "Real return (est.)"        : f"{real_return:+.1f}%",
            "AUM affected"              : _fmt_cr(total_aum),
            "Instruments used"          : ", ".join(types_used),
        },
        affected_ids = over_cons["Client_ID"].tolist(),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RULE 9 — Poor Risk-Adjusted Return
# ─────────────────────────────────────────────────────────────────────────────
def _rule_poor_risk_adjusted(df: pd.DataFrame) -> Optional[Recommendation]:
    """
    WHAT IT DETECTS
    ───────────────
    Clients where ROI / Risk_Score < RISK_ADJ_MIN (2.0).
    A Risk Score of 8 should produce at least 16% ROI to be "worth it."
    Clients below this threshold are taking on risk without reward.

    SEVERITY: WARNING — inefficient risk-return trade-off.
    """
    df_calc = df.copy()
    df_calc["risk_adj"] = df_calc["ROI_Pct"] / df_calc["Risk_Score"]
    poor = df_calc[df_calc["risk_adj"] < RISK_ADJ_MIN]

    if poor.empty:
        return None

    avg_risk     = poor["Risk_Score"].mean()
    avg_roi      = poor["ROI_Pct"].mean()
    avg_adj      = poor["risk_adj"].mean()
    worst_client = poor.loc[poor["risk_adj"].idxmin()]
    aum_affected = poor["Portfolio_Value_INR"].sum()

    return Recommendation(
        severity    = "WARNING",
        category    = "Risk Efficiency",
        icon        = "⚖️",
        priority    = 9,
        title       = f"{len(poor)} Clients Taking Risk Without Proportional Reward",
        explanation = (
            f"{len(poor)} client(s) have a Risk-Adjusted Return below {RISK_ADJ_MIN:.1f}x "
            f"(ROI ÷ Risk Score). They average a Risk Score of {avg_risk:.1f} "
            f"but only earn {avg_roi:.1f}% ROI — a ratio of {avg_adj:.2f}x. "
            f"The worst case: {worst_client['Client_Name']} has Risk Score "
            f"{worst_client['Risk_Score']} but ROI of only {worst_client['ROI_Pct']:.1f}%."
        ),
        action = (
            f"For each affected client, run a portfolio efficiency review. Either "
            f"(a) reduce risk by shifting to lower-volatility instruments that still "
            f"deliver similar ROI, or (b) switch to higher-performing instruments "
            f"within the same risk band. Target a Risk-Adjusted Return ≥ {RISK_ADJ_MIN:.1f}x."
        ),
        metrics = {
            "Inefficient clients"   : len(poor),
            "Avg Risk Score"        : f"{avg_risk:.1f}/10",
            "Avg ROI"               : _fmt_pct(avg_roi),
            "Avg risk-adj ratio"    : f"{avg_adj:.2f}x",
            "AUM affected"          : _fmt_cr(aum_affected),
        },
        affected_ids = poor["Client_ID"].tolist(),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RULE 10 — Sector Correlation Risk
# ─────────────────────────────────────────────────────────────────────────────
def _rule_sector_correlation(df: pd.DataFrame) -> Optional[Recommendation]:
    """
    WHAT IT DETECTS
    ───────────────
    When two or more high-correlation sectors together hold > 40% of AUM.
    Banking & Finance + Technology are historically correlated (both suffer
    in credit/liquidity crises).

    SEVERITY: WARNING — systemic portfolio risk.
    """
    # Known correlated pairs in Indian markets
    correlated_groups = [
        (["Banking & Finance", "Technology"],   "credit and tech cycles"),
        (["Energy", "Infrastructure"],          "capex and commodity cycles"),
        (["Pharmaceuticals", "Healthcare"],     "healthcare regulatory cycles"),
    ]

    sector_aum = df.groupby("Sector")["Portfolio_Value_INR"].sum()
    total_aum  = sector_aum.sum()

    for group, cycle_name in correlated_groups:
        present = [s for s in group if s in sector_aum.index]
        if len(present) < 2:
            continue
        combined_aum = sector_aum[present].sum()
        combined_pct = combined_aum / total_aum * 100

        if combined_pct > 35:
            return Recommendation(
                severity    = "WARNING",
                category    = "Correlation Risk",
                icon        = "🔗",
                priority    = 10,
                title       = (
                    f"{' + '.join(present)} Together Hold {combined_pct:.1f}% of AUM "
                    f"— Correlated Sector Risk"
                ),
                explanation = (
                    f"{' and '.join(present)} are historically correlated through "
                    f"{cycle_name}. Together they account for {combined_pct:.1f}% "
                    f"of total AUM ({_fmt_cr(combined_aum)}). A macro event affecting "
                    f"both sectors simultaneously could cause a correlated drawdown "
                    f"in a disproportionate share of the firm's book."
                ),
                action = (
                    f"Diversify into sectors with low correlation: Healthcare, Consumer "
                    f"Goods, or FMCG. Target a maximum of 35% in any correlated sector "
                    f"group. Review the correlation assumption quarterly — sector "
                    f"correlations can shift during market regime changes."
                ),
                metrics = {
                    "Correlated sectors"  : " + ".join(present),
                    "Combined AUM"        : _fmt_cr(combined_aum),
                    "Combined exposure"   : _fmt_pct(combined_pct),
                    "Correlation driver"  : cycle_name,
                },
            )
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  MASTER FUNCTION — run all rules
# ─────────────────────────────────────────────────────────────────────────────
def generate_recommendations(df: pd.DataFrame) -> list[Recommendation]:
    """
    Runs all 10 rules against the filtered DataFrame.
    Returns a list of Recommendation objects sorted by priority (most urgent first).

    Parameters
    ──────────
    df : pd.DataFrame
        The FILTERED dataset from apply_filters(). Pass the filtered df
        so insights react to sidebar filter changes automatically.

    Returns
    ────────
    list[Recommendation]
        Only rules that FIRED (found a condition) are returned.
        Rules that found nothing return None and are excluded.

    Usage in app.py:
        recommendations = generate_recommendations(df)
        render_recommendations(recommendations)
    """
    rules = [
        _rule_risk_misalignment,
        _rule_aum_concentration,
        _rule_underperforming_sectors,
        _rule_best_sector_opportunity,
        _rule_underperforming_types,
        _rule_hni_opportunity,
        _rule_top_performers,
        _rule_over_conservative,
        _rule_poor_risk_adjusted,
        _rule_sector_correlation,
    ]

    results = []
    for rule in rules:
        try:
            rec = rule(df)
            if rec is not None:
                results.append(rec)
        except Exception:
            # Silently skip failed rules — never crash the dashboard
            pass

    # Sort: CRITICAL first, then WARNING, then POSITIVE, then by priority number
    severity_order = {"CRITICAL": 0, "WARNING": 1, "POSITIVE": 2}
    results.sort(key=lambda r: (severity_order.get(r.severity, 9), r.priority))

    return results


# ─────────────────────────────────────────────────────────────────────────────
#  RENDER FUNCTION — draws all recommendation cards in Streamlit
# ─────────────────────────────────────────────────────────────────────────────

# Colour palette for each severity level
_SEVERITY_STYLES = {
    "CRITICAL": {
        "border"    : "#E74C3C",
        "bg"        : "rgba(231,76,60,0.05)",
        "badge_bg"  : "#FDEDEC",
        "badge_fg"  : "#922B21",
        "label"     : "CRITICAL",
        "dot_color" : "#E74C3C",
    },
    "WARNING": {
        "border"    : "#F39C12",
        "bg"        : "rgba(243,156,18,0.05)",
        "badge_bg"  : "#FEF6E7",
        "badge_fg"  : "#8A5A00",
        "label"     : "WARNING",
        "dot_color" : "#F39C12",
    },
    "POSITIVE": {
        "border"    : "#2ECC71",
        "bg"        : "rgba(46,204,113,0.05)",
        "badge_bg"  : "#E9FAF1",
        "badge_fg"  : "#1A7A47",
        "label"     : "POSITIVE",
        "dot_color" : "#2ECC71",
    },
}


def _recommendation_card_html(rec: Recommendation) -> str:
    """
    Builds the HTML for one recommendation card.
    Called by render_recommendations() for each item in the list.
    """
    style  = _SEVERITY_STYLES.get(rec.severity, _SEVERITY_STYLES["WARNING"])

    # Build metrics row HTML
    metrics_html = ""
    if rec.metrics:
        pills = "".join(
            f'<span style="background:#F0F2F5;border-radius:6px;padding:4px 10px;'
            f'font-size:11px;color:#374151;white-space:nowrap">'
            f'<b style="color:#111827">{k}:</b> {v}</span> '
            for k, v in rec.metrics.items()
        )
        metrics_html = (
            f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:12px">'
            f'{pills}</div>'
        )

    # Affected client count badge
    affected_html = ""
    if rec.affected_ids:
        affected_html = (
            f'<span style="font-size:11px;color:#6B7280;margin-left:8px">'
            f'↳ {len(rec.affected_ids)} client(s) affected</span>'
        )

    return f"""
<div style="
background   : {style['bg']};
border       : 1px solid {style['border']};
border-left  : 4px solid {style['border']};
border-radius: 10px;
padding      : 16px 18px;
margin-bottom: 12px;
">
<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px">
<span style="font-size:20px;line-height:1;flex-shrink:0">{rec.icon}</span>
<div style="flex:1;min-width:0">
<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px">
<span style="
    background:{style['badge_bg']};color:{style['badge_fg']};
    font-size:10px;font-weight:700;padding:2px 8px;
    border-radius:4px;letter-spacing:0.5px
">{style['label']}</span>
<span style="
    background:#F0F2F5;color:#6B7280;
    font-size:10px;font-weight:500;padding:2px 8px;
    border-radius:4px
">{rec.category}</span>
{affected_html}
</div>
<div style="font-size:14px;font-weight:700;color:#0A2342;line-height:1.3">
{rec.title}
</div>
</div>
</div>

<div style="font-size:13px;color:#4B5563;line-height:1.65;
padding-left:30px;margin-bottom:8px">
{rec.explanation}
</div>

<div style="
background : rgba(255,255,255,0.7);
border     : 1px solid rgba(0,0,0,0.07);
border-radius: 7px;
padding    : 10px 14px;
margin-left: 30px;
">
<div style="font-size:11px;font-weight:700;color:#374151;
    text-transform:uppercase;letter-spacing:0.6px;
    margin-bottom:4px">💬 Suggested Action</div>
<div style="font-size:12.5px;color:#374151;line-height:1.6">
{rec.action}
</div>
</div>

<div style="padding-left:30px">{metrics_html}</div>
</div>
    """


def render_recommendations(recommendations: list[Recommendation]) -> None:
    """
    Renders the complete recommendations section in the Streamlit app.

    Layout:
    ─────────────────────────────────────────────────────────────────
    • Section header with summary counts (X critical, Y warnings, Z positive)
    • Severity filter tabs (All | Critical | Warnings | Positive)
    • Two-column card grid (cards fill from top-left)
    • Empty state message if no recommendations fire

    Parameters
    ──────────
    recommendations : list[Recommendation]
        Output of generate_recommendations(df). Can be empty.

    Usage in app.py:
        recommendations = generate_recommendations(df)
        render_recommendations(recommendations)
    """
    # ── Section header ────────────────────────────────────────────────────
    n_critical = sum(1 for r in recommendations if r.severity == "CRITICAL")
    n_warning  = sum(1 for r in recommendations if r.severity == "WARNING")
    n_positive = sum(1 for r in recommendations if r.severity == "POSITIVE")

    st.markdown(
        '<div style="font-size:18px;font-weight:700;color:#0A2342;'
        'padding-bottom:8px;border-bottom:2px solid #E8ECF0;margin-bottom:16px">'
        '💡 Smart Portfolio Recommendations'
        '</div>',
        unsafe_allow_html=True,
    )

    # Summary badge row
    st.markdown(f"""
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;align-items:center">
        <div style="font-size:12px;color:#6B7280;font-weight:500">
            {len(recommendations)} insights generated from {n_critical + n_warning + n_positive} rules
        </div>
        <span style="background:#FDEDEC;color:#922B21;font-size:12px;font-weight:700;
                     padding:3px 10px;border-radius:20px">
            🚨 {n_critical} Critical
        </span>
        <span style="background:#FEF6E7;color:#8A5A00;font-size:12px;font-weight:700;
                     padding:3px 10px;border-radius:20px">
            ⚠️ {n_warning} Warnings
        </span>
        <span style="background:#E9FAF1;color:#1A7A47;font-size:12px;font-weight:700;
                     padding:3px 10px;border-radius:20px">
            ✅ {n_positive} Positive
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Empty state ───────────────────────────────────────────────────────
    if not recommendations:
        st.markdown("""
        <div style="text-align:center;padding:40px;background:#F9FAFB;
                    border:1px solid #E5E7EB;border-radius:12px">
            <div style="font-size:36px;margin-bottom:8px">✅</div>
            <div style="font-size:15px;font-weight:600;color:#111827">
                No Issues Detected
            </div>
            <div style="font-size:13px;color:#6B7280;margin-top:4px">
                The filtered portfolio meets all health thresholds.
                Try a different filter combination to surface more insights.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Severity filter tabs ──────────────────────────────────────────────
    # st.radio() creates tab-like buttons to filter by severity
    filter_choice = st.radio(
        label             = "Show",
        options           = ["All", "Critical", "Warnings", "Positive"],
        horizontal        = True,
        label_visibility  = "collapsed",
        key               = "rec_filter",
    )

    severity_map = {
        "All"      : ["CRITICAL", "WARNING", "POSITIVE"],
        "Critical" : ["CRITICAL"],
        "Warnings" : ["WARNING"],
        "Positive" : ["POSITIVE"],
    }
    visible = [r for r in recommendations
               if r.severity in severity_map[filter_choice]]

    if not visible:
        st.info(f"No {filter_choice.lower()} recommendations for the current filter selection.")
        return

    # ── Two-column card layout ────────────────────────────────────────────
    col_left, col_right = st.columns(2, gap="medium")

    for i, rec in enumerate(visible):
        # Alternate cards between left and right columns
        target_col = col_left if i % 2 == 0 else col_right
        with target_col:
            st.markdown(
                _recommendation_card_html(rec),
                unsafe_allow_html=True,
            )