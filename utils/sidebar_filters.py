"""
utils/sidebar_filters.py
========================
Professional sidebar filter system for the WIN Advisors Dashboard.

WHAT THIS FILE DOES
────────────────────
This module owns EVERYTHING related to the sidebar:
  • CSS injection     → dark navy gradient, styled inputs, pill tags
  • Brand header      → logo, firm name, tagline
  • 5 filter widgets  → sector, investment type, risk label, goal, ROI slider
  • Filter state      → returns a FilterState dataclass with all selections
  • apply_filters()   → applies every filter to a DataFrame in one call
  • filter_summary()  → compact display of active filters below the sidebar

HOW TO USE IN app.py  (3 steps — nothing else needed)
──────────────────────────────────────────────────────
  STEP 1 — Import at the top of app.py:
    from utils.sidebar_filters import render_sidebar, apply_filters

  STEP 2 — Render the sidebar (before any charts or KPIs):
    filter_state = render_sidebar(df_full)

  STEP 3 — Apply filters to get the filtered DataFrame:
    df = apply_filters(df_full, filter_state)

  After step 3, use `df` everywhere — every chart, KPI card,
  recommendation, and data table will react to the sidebar automatically.
  Streamlit's re-run model handles all the reactivity for free.

WHY A SEPARATE MODULE?
───────────────────────
Keeping sidebar logic here means app.py stays under 100 lines
and you can change any filter without touching the main layout.
It also makes the filters reusable — drop this file into any
future Streamlit project and it just works.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import streamlit as st
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────────────────────────────────────────────

# Each filter has an emoji icon shown next to its label
FILTER_ICONS = {
    "sector"   : "🏭",
    "inv_type" : "📦",
    "risk"     : "⚡",
    "goal"     : "🎯",
    "roi"      : "📈",
}

# Risk labels in the correct order (Low → High) for the multiselect
RISK_ORDER = ["Very Low", "Low", "Moderate", "High", "Very High"]

# Colour used on the pill tag for each risk level (shown in the filter summary)
RISK_COLORS = {
    "Very Low" : ("#D5F5E3", "#1E8449"),
    "Low"      : ("#D1F2EB", "#148F77"),
    "Moderate" : ("#FEF9E7", "#9A7D0A"),
    "High"     : ("#FDEBD0", "#A04000"),
    "Very High": ("#FADBD8", "#922B21"),
}

# Goal icons make the multiselect easier to scan
GOAL_ICONS = {
    "Wealth Creation"    : "💰",
    "Retirement Planning": "🏖",
    "Child Education"    : "🎓",
    "Tax Saving"         : "🧾",
    "Emergency Fund"     : "🛡",
    "Home Purchase"      : "🏠",
    "Business Expansion" : "🚀",
    "Passive Income"     : "💤",
}


# ─────────────────────────────────────────────────────────────────────────────
# FILTER STATE  —  holds every selection the user makes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FilterState:
    """
    A simple container that holds the current value of every sidebar filter.

    WHAT IS A DATACLASS?
    ────────────────────
    @dataclass is a Python decorator that auto-generates __init__, __repr__,
    and __eq__ for a class. It's like a neat dictionary but with named fields.
    Using a dataclass here (instead of a plain dict) means your IDE can
    auto-complete `filter_state.sectors` — no typos, no KeyError bugs.

    Fields
    ──────
    sectors      list of selected sector strings
    inv_types    list of selected investment type strings
    risk_labels  list of selected risk label strings
    goals        list of selected financial goal strings
    roi_range    tuple (min_roi, max_roi) from the slider
    """
    sectors    : list[str] = field(default_factory=list)
    inv_types  : list[str] = field(default_factory=list)
    risk_labels: list[str] = field(default_factory=list)
    goals      : list[str] = field(default_factory=list)
    roi_range  : tuple     = (0.0, 100.0)


# ─────────────────────────────────────────────────────────────────────────────
# CSS INJECTION
# ─────────────────────────────────────────────────────────────────────────────

def _inject_sidebar_css() -> None:
    """
    Injects all CSS needed to style the sidebar.
    Called once inside render_sidebar() — do not call separately.

    WHY INJECT CSS HERE AND NOT IN style.css?
    ─────────────────────────────────────────
    The sidebar CSS references specific Streamlit test-IDs that can change
    across Streamlit versions. Keeping it here makes it easier to update
    without breaking the main stylesheet.
    """
    st.markdown("""
    <style>
    /* ── Sidebar shell ─────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background    : linear-gradient(180deg, #0A2342 0%, #0D2D55 60%, #0A1E38 100%);
        border-right  : 1px solid rgba(255,255,255,0.06);
        min-width     : 260px;
    }
    /* All text inside sidebar */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: #BDC9D9 !important;
    }

    /* ── Filter section card ────────────────────────────────────────── */
    .filter-card {
        background    : rgba(255,255,255,0.05);
        border        : 1px solid rgba(255,255,255,0.09);
        border-radius : 10px;
        padding       : 12px 14px 10px 14px;
        margin-bottom : 10px;
    }
    .filter-label {
        font-size     : 11px;
        font-weight   : 600;
        color         : rgba(255,255,255,0.5) !important;
        text-transform: uppercase;
        letter-spacing: 0.7px;
        margin-bottom : 8px;
        display       : flex;
        align-items   : center;
        gap           : 6px;
    }

    /* ── Multiselect inputs ─────────────────────────────────────────── */
    [data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] {
        background    : rgba(255,255,255,0.07) !important;
        border        : 1px solid rgba(255,255,255,0.14) !important;
        border-radius : 8px !important;
    }
    [data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"]:focus-within {
        border-color  : rgba(30,111,186,0.8) !important;
        box-shadow    : 0 0 0 2px rgba(30,111,186,0.25) !important;
    }
    /* Pill tags inside multiselect */
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background    : #1E6FBA !important;
        border-radius : 6px !important;
    }
    [data-testid="stSidebar"] [data-baseweb="tag"] span {
        color         : #FFFFFF !important;
        font-size     : 11px !important;
    }

    /* ── Slider ─────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] [data-testid="stSlider"] > div {
        padding-top   : 4px;
    }
    /* Slider track */
    [data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {
        background    : #1E6FBA !important;
        border        : 2px solid #FFFFFF !important;
    }

    /* ── Reset button ───────────────────────────────────────────────── */
    [data-testid="stSidebar"] .stButton > button {
        background    : rgba(30,111,186,0.20);
        border        : 1px solid rgba(30,111,186,0.50);
        border-radius : 8px;
        color         : #7BB8F5;
        font-size     : 12px;
        font-weight   : 600;
        padding       : 6px 0;
        width         : 100%;
        transition    : all 0.15s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background    : rgba(30,111,186,0.38);
        border-color  : rgba(30,111,186,0.80);
        color         : #FFFFFF;
    }

    /* ── Dividers ───────────────────────────────────────────────────── */
    [data-testid="stSidebar"] hr {
        border-color  : rgba(255,255,255,0.09);
        margin        : 12px 0;
    }

    /* ── Filter summary bar (below sidebar, inside main area) ───────── */
    .filter-summary {
        display       : flex;
        align-items   : center;
        gap           : 8px;
        flex-wrap     : wrap;
        padding       : 8px 14px;
        background    : rgba(10,35,66,0.04);
        border        : 1px solid #E8ECF0;
        border-radius : 10px;
        margin-bottom : 18px;
    }
    .fs-label {
        font-size     : 11px;
        font-weight   : 600;
        color         : #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        flex-shrink   : 0;
    }
    .fs-pill {
        display       : inline-flex;
        align-items   : center;
        gap           : 4px;
        font-size     : 11.5px;
        font-weight   : 500;
        padding       : 3px 9px;
        border-radius : 20px;
        white-space   : nowrap;
    }
    .fs-count {
        font-size     : 12px;
        font-weight   : 700;
        color         : #0A2342;
        margin-left   : auto;
        flex-shrink   : 0;
        background    : #EAF2FB;
        padding       : 3px 10px;
        border-radius : 20px;
    }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — filter count badge
# ─────────────────────────────────────────────────────────────────────────────

def _selection_label(selected: list, all_options: list, singular: str) -> str:
    """
    Returns a compact label describing what's selected.
    Examples:
      • All 10 selected       → "All sectors"
      • 1 selected            → "Technology"
      • 2 selected            → "2 sectors"
      • 0 selected (edge)     → "None"
    """
    n     = len(selected)
    total = len(all_options)
    if n == 0:
        return "None"
    elif n == total:
        return f"All {singular}s"
    elif n == 1:
        return selected[0]
    else:
        return f"{n} {singular}s"


def _count_badge(n: int, total: int) -> str:
    """Returns a small HTML badge showing n / total."""
    pct = int(n / total * 100) if total > 0 else 0
    col = "#2ECC71" if pct == 100 else "#1E6FBA" if pct >= 50 else "#F39C12"
    return (
        f'<span style="background:rgba(30,111,186,0.1);color:{col};'
        f'font-size:11px;font-weight:700;padding:1px 7px;'
        f'border-radius:10px">{n}/{total}</span>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# INDIVIDUAL FILTER BUILDERS
# Each _filter_*() function renders one filter widget and returns the selection.
# ─────────────────────────────────────────────────────────────────────────────

def _filter_sector(df: pd.DataFrame) -> list[str]:
    """
    FILTER 1 — Sector
    ─────────────────
    A multiselect of all 10 economic sectors.
    Options are sorted alphabetically. Default = all selected.
    The count badge (22/100) updates dynamically as user selects.

    WHY MULTISELECT?
    ────────────────
    An advisor might want to compare "Technology vs Healthcare" side-by-side.
    A single-select dropdown would force them to pick just one — multiselect
    lets them build any comparison they need.
    """
    all_opts = sorted(df["Sector"].unique().tolist())

    st.markdown(
        f'<div class="filter-label">{FILTER_ICONS["sector"]} Sector</div>',
        unsafe_allow_html=True,
    )
    selected = st.multiselect(
        label            = "Sector",
        options          = all_opts,
        default          = all_opts,          # all selected by default
        label_visibility = "collapsed",       # label shown via HTML above
        key              = "filter_sector",
    )
    # Show "X selected / Y total" badge inline
    count_in_df = df[df["Sector"].isin(selected)]["Sector"].count() if selected else 0
    st.markdown(
        f'<div style="font-size:11px;color:rgba(255,255,255,0.35);'
        f'margin-top:-4px;margin-bottom:4px">'
        f'{_selection_label(selected, all_opts, "sector")} · '
        f'{count_in_df} clients</div>',
        unsafe_allow_html=True,
    )
    return selected if selected else all_opts   # guard: never return empty


def _filter_investment_type(df: pd.DataFrame) -> list[str]:
    """
    FILTER 2 — Investment Type
    ──────────────────────────
    Multiselect of 8 asset classes (Equity, Bonds, ETF, etc.).

    The options are sorted by AUM descending so the most significant
    types appear at the top of the list — this is a UX improvement
    over alphabetical sorting for financial data.
    """
    # Sort options by total AUM descending — most significant type first
    type_aum = (
        df.groupby("Investment_Type")["Portfolio_Value_INR"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    st.markdown(
        f'<div class="filter-label">{FILTER_ICONS["inv_type"]} Investment Type</div>',
        unsafe_allow_html=True,
    )
    selected = st.multiselect(
        label            = "Investment Type",
        options          = type_aum,
        default          = type_aum,
        label_visibility = "collapsed",
        key              = "filter_inv_type",
    )
    count_in_df = df[df["Investment_Type"].isin(selected)].shape[0] if selected else 0
    st.markdown(
        f'<div style="font-size:11px;color:rgba(255,255,255,0.35);'
        f'margin-top:-4px;margin-bottom:4px">'
        f'{_selection_label(selected, type_aum, "type")} · '
        f'{count_in_df} clients</div>',
        unsafe_allow_html=True,
    )
    return selected if selected else type_aum


def _filter_risk_label(df: pd.DataFrame) -> list[str]:
    """
    FILTER 3 — Risk Label
    ──────────────────────
    Multiselect of 5 risk tiers: Very Low → Very High.
    Options are shown in LOW→HIGH order (not alphabetical)
    so the user reads them as a spectrum.

    The Risk_Label column must already exist in the DataFrame.
    It's created by data_loader.py from Risk_Score using classify_risk().

    BUSINESS USE CASE
    ─────────────────
    An advisor preparing for a volatile market might filter to
    "High + Very High" clients to identify who to call proactively.
    Filtering to "Very Low + Low" shows the ultra-conservative book.
    """
    # Preserve the conceptual order (not alphabetical)
    present_risks = [r for r in RISK_ORDER if r in df["Risk_Label"].unique()]

    st.markdown(
        f'<div class="filter-label">{FILTER_ICONS["risk"]} Risk Level</div>',
        unsafe_allow_html=True,
    )
    selected = st.multiselect(
        label            = "Risk Level",
        options          = present_risks,
        default          = present_risks,
        label_visibility = "collapsed",
        key              = "filter_risk",
    )
    count_in_df = df[df["Risk_Label"].isin(selected)].shape[0] if selected else 0
    st.markdown(
        f'<div style="font-size:11px;color:rgba(255,255,255,0.35);'
        f'margin-top:-4px;margin-bottom:4px">'
        f'{_selection_label(selected, present_risks, "level")} · '
        f'{count_in_df} clients</div>',
        unsafe_allow_html=True,
    )
    return selected if selected else present_risks


def _filter_financial_goal(df: pd.DataFrame) -> list[str]:
    """
    FILTER 4 — Financial Goal
    ──────────────────────────
    Multiselect of 8 financial goals.
    Each option is prefixed with its emoji (from GOAL_ICONS) so
    the list is scannable at a glance without reading every word.
    Options are sorted by frequency (most common goal first).

    BUSINESS USE CASE
    ─────────────────
    An advisor reviewing the "Retirement Planning" segment can
    instantly filter to only those clients — then check if their
    risk profiles and ROI are appropriate for retirement timelines.
    """
    # Sort by frequency — most common goals appear first
    goal_freq  = df["Financial_Goal"].value_counts().index.tolist()

    # Prefix each option with its icon
    def label(g: str) -> str:
        return f"{GOAL_ICONS.get(g, '•')} {g}"

    options_raw   = goal_freq                          # raw strings for filtering
    options_disp  = [label(g) for g in goal_freq]     # display strings with icons

    # Build a mapping so the user's display selection maps back to raw values
    disp_to_raw = {label(g): g for g in goal_freq}

    st.markdown(
        f'<div class="filter-label">{FILTER_ICONS["goal"]} Financial Goal</div>',
        unsafe_allow_html=True,
    )
    selected_disp = st.multiselect(
        label            = "Financial Goal",
        options          = options_disp,
        default          = options_disp,
        label_visibility = "collapsed",
        key              = "filter_goal",
    )

    # Translate display labels back to raw goal strings
    selected_raw  = [disp_to_raw[d] for d in selected_disp if d in disp_to_raw]

    count_in_df = df[df["Financial_Goal"].isin(selected_raw)].shape[0] if selected_raw else 0
    st.markdown(
        f'<div style="font-size:11px;color:rgba(255,255,255,0.35);'
        f'margin-top:-4px;margin-bottom:4px">'
        f'{_selection_label(selected_raw, options_raw, "goal")} · '
        f'{count_in_df} clients</div>',
        unsafe_allow_html=True,
    )
    return selected_raw if selected_raw else options_raw


def _filter_roi_range(df: pd.DataFrame) -> tuple[float, float]:
    """
    FILTER 5 — ROI Range Slider
    ────────────────────────────
    A dual-handle range slider that lets the user set a minimum
    and maximum ROI threshold. Clients outside this range are excluded.

    The slider range is set from the actual data minimum (5.3%) to
    maximum (35.3%) — not a fixed range. This means it adapts if
    the dataset is replaced with different data.

    Step = 0.5 → half-percent precision, which is meaningful
    for investment decisions without being overly granular.

    BUSINESS USE CASE
    ─────────────────
    "Show me only clients earning between 15% and 35% ROI" →
    quickly isolates the high-performing cohort for case studies.
    "Show me only clients below 10% ROI" → surfaces the clients
    who need urgent portfolio reviews.

    HOW st.slider() WORKS FOR RANGES
    ──────────────────────────────────
    When value= is a tuple (min, max), Streamlit automatically
    creates a two-handle range slider. It returns a tuple.
    """
    roi_min = float(round(df["ROI_Pct"].min(), 1))
    roi_max = float(round(df["ROI_Pct"].max(), 1))

    st.markdown(
        f'<div class="filter-label">{FILTER_ICONS["roi"]} ROI Range</div>',
        unsafe_allow_html=True,
    )

    selected = st.slider(
        label    = "ROI Range",
        min_value= roi_min,
        max_value= roi_max,
        value    = (roi_min, roi_max),   # default: full range
        step     = 0.5,
        format   = "%.1f%%",             # show % symbol on slider handles
        label_visibility = "collapsed",
        key      = "filter_roi",
    )

    # Show current selection as text beneath the slider
    clients_in_range = df["ROI_Pct"].between(selected[0], selected[1]).sum()
    benchmark_line   = "above benchmark ✓" if selected[0] >= 12.0 else "includes sub-benchmark"
    st.markdown(
        f'<div style="font-size:11px;color:rgba(255,255,255,0.35);margin-top:2px">'
        f'{selected[0]:.1f}% → {selected[1]:.1f}% · '
        f'{clients_in_range} clients · {benchmark_line}</div>',
        unsafe_allow_html=True,
    )
    return selected


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar(df: pd.DataFrame) -> FilterState:
    """
    Renders the entire sidebar and returns a FilterState with all selections.

    This is the ONLY function you call from app.py.
    Everything else in this file is an internal helper.

    Parameters
    ──────────
    df : pd.DataFrame
        The FULL unfiltered dataset (df_full from load_portfolio()).
        We pass the full dataset so the filter options always show
        all possible values, even when other filters are active.
        (This prevents the "filter disappearing" problem where an option
        vanishes because another filter has already excluded all its rows.)

    Returns
    ────────
    FilterState
        A dataclass with 5 fields — one per filter.
        Pass it directly to apply_filters(df_full, filter_state).

    HOW STREAMLIT'S RE-RUN MODEL WORKS WITH FILTERS
    ─────────────────────────────────────────────────
    When a user changes ANY widget, Streamlit re-runs the ENTIRE script
    from top to bottom. This means:
      1. render_sidebar() is called again
      2. st.multiselect() and st.slider() return the NEW values
      3. FilterState is created with the new values
      4. apply_filters() produces a new filtered DataFrame
      5. Every chart and KPI re-renders with the new data

    You don't need to write any callback or event handler.
    Streamlit's re-run model handles all reactivity automatically.
    """
    _inject_sidebar_css()

    with st.sidebar:

        # ── Brand header ──────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center;padding:22px 0 14px">
            <div style="font-size:34px;margin-bottom:6px">💼</div>
            <div style="color:#FFFFFF;font-size:19px;font-weight:800;
                        letter-spacing:-0.3px;line-height:1.2">WIN ADVISORS</div>
            <div style="color:rgba(255,255,255,0.42);font-size:11px;
                        margin-top:4px;letter-spacing:0.4px">
                Portfolio Intelligence Platform
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<hr>', unsafe_allow_html=True)

        # ── Section label ─────────────────────────────────────────────
        st.markdown("""
        <div style="font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);
                    text-transform:uppercase;letter-spacing:1px;
                    margin-bottom:10px">
            ◈  Dashboard Filters
        </div>
        """, unsafe_allow_html=True)

        # ── Filter 1: Sector ──────────────────────────────────────────
        sel_sectors   = _filter_sector(df)

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

        # ── Filter 2: Investment Type ─────────────────────────────────
        sel_inv_types = _filter_investment_type(df)

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

        # ── Filter 3: Risk Level ──────────────────────────────────────
        sel_risks     = _filter_risk_label(df)

        st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

        # ── Filter 4: Financial Goal ──────────────────────────────────
        sel_goals     = _filter_financial_goal(df)

        st.markdown('<hr>', unsafe_allow_html=True)

        # ── Filter 5: ROI Range Slider ────────────────────────────────
        sel_roi       = _filter_roi_range(df)

        st.markdown('<hr>', unsafe_allow_html=True)

        # ── Live client count ─────────────────────────────────────────
        # Apply filters now to show the live count in the sidebar itself
        filtered_count = apply_filters(
            df,
            FilterState(
                sectors     = sel_sectors,
                inv_types   = sel_inv_types,
                risk_labels = sel_risks,
                goals       = sel_goals,
                roi_range   = sel_roi,
            )
        ).shape[0]

        total_count = len(df)
        pct_shown   = int(filtered_count / total_count * 100) if total_count else 0
        bar_color   = "#2ECC71" if pct_shown == 100 else "#1E6FBA" if pct_shown >= 40 else "#F39C12"

        st.markdown(f"""
        <div style="text-align:center;margin-bottom:14px">
            <div style="font-size:28px;font-weight:800;color:#FFFFFF;
                        line-height:1">{filtered_count}</div>
            <div style="font-size:11px;color:rgba(255,255,255,0.45);margin-top:3px">
                clients match filters
            </div>
            <div style="background:rgba(255,255,255,0.1);border-radius:4px;
                        height:5px;margin:10px 0 4px;overflow:hidden">
                <div style="width:{pct_shown}%;height:100%;
                            background:{bar_color};border-radius:4px;
                            transition:width 0.3s ease"></div>
            </div>
            <div style="font-size:10px;color:rgba(255,255,255,0.30)">
                {pct_shown}% of {total_count} total clients
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Reset all filters button ──────────────────────────────────
        # st.rerun() re-executes the entire script, which clears all
        # widget states back to their default= values.
        if st.button("↺  Reset All Filters", use_container_width=True):
            st.rerun()

        # ── Footer ────────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center;margin-top:16px;
                    font-size:10px;color:rgba(255,255,255,0.18)">
            WIN ADVISORS · Internal Use Only
        </div>
        """, unsafe_allow_html=True)

    # Build and return the FilterState dataclass
    return FilterState(
        sectors     = sel_sectors,
        inv_types   = sel_inv_types,
        risk_labels = sel_risks,
        goals       = sel_goals,
        roi_range   = sel_roi,
    )


# ─────────────────────────────────────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────────────────────────────────────

def apply_filters(df: pd.DataFrame, fs: FilterState) -> pd.DataFrame:
    """
    Applies all 5 filters to the DataFrame and returns a filtered copy.

    Parameters
    ──────────
    df : pd.DataFrame   Full unfiltered dataset
    fs : FilterState    Selections from render_sidebar()

    Returns
    ────────
    pd.DataFrame        Filtered subset — used for ALL downstream rendering

    HOW THE MASK WORKS
    ──────────────────
    We build one boolean mask per filter using Pandas .isin() and .between().
    Then we combine them with & (AND logic — client must pass ALL filters).

    isin()    → True if the cell's value is in the selected list
    between() → True if the value falls within [min, max] inclusive

    The copy() at the end prevents the "SettingWithCopyWarning" —
    modifications to df_filtered won't affect df_full.
    """
    # Guard: if any filter has empty selection, return the full DataFrame
    # (prevents the dashboard going blank when a user deselects everything)
    if not fs.sectors or not fs.inv_types or not fs.risk_labels or not fs.goals:
        return df.copy()

    mask = (
        df["Sector"].isin(fs.sectors)           # AND
        & df["Investment_Type"].isin(fs.inv_types)   # AND
        & df["Risk_Label"].isin(fs.risk_labels)      # AND
        & df["Financial_Goal"].isin(fs.goals)        # AND
        & df["ROI_Pct"].between(fs.roi_range[0], fs.roi_range[1])
    )
    filtered = df[mask].copy()

    # If somehow all rows are filtered out, return full df with a warning
    # This prevents blank charts crashing the dashboard
    if filtered.empty:
        st.warning(
            "⚠️ No clients match the current filters. "
            "Showing all clients. Please adjust your selection.",
            icon="⚠️",
        )
        return df.copy()

    return filtered


# ─────────────────────────────────────────────────────────────────────────────
# FILTER SUMMARY BAR  —  shown at the top of the main content area
# ─────────────────────────────────────────────────────────────────────────────

def render_filter_summary(df_full: pd.DataFrame,
                          df_filtered: pd.DataFrame,
                          fs: FilterState) -> None:
    """
    Renders a compact one-line summary bar in the MAIN content area
    (not the sidebar) showing which filters are currently active.

    This gives users a persistent reminder of what's been filtered,
    even when the sidebar is collapsed on smaller screens.

    Parameters
    ──────────
    df_full     : Full unfiltered dataset
    df_filtered : Result of apply_filters()
    fs          : Current FilterState from render_sidebar()
    """
    n_shown = len(df_filtered)
    n_total = len(df_full)
    is_filtered = n_shown < n_total

    # Build pill HTML for each active filter
    pills = []

    # Sector pill
    s_label = _selection_label(fs.sectors, sorted(df_full["Sector"].unique()), "sector")
    pills.append(
        f'<span class="fs-pill" style="background:#EAF2FB;color:#185FA5">'
        f'🏭 {s_label}</span>'
    )

    # Investment type pill
    all_types = df_full["Investment_Type"].unique().tolist()
    t_label = _selection_label(fs.inv_types, all_types, "type")
    pills.append(
        f'<span class="fs-pill" style="background:#E9FAF1;color:#1A7A47">'
        f'📦 {t_label}</span>'
    )

    # Risk pill
    r_label = _selection_label(fs.risk_labels, RISK_ORDER, "level")
    risk_bg = "#FEF6E7" if "High" in fs.risk_labels else "#E9FAF1"
    risk_fg = "#8A5A00" if "High" in fs.risk_labels else "#1A7A47"
    pills.append(
        f'<span class="fs-pill" style="background:{risk_bg};color:{risk_fg}">'
        f'⚡ {r_label}</span>'
    )

    # ROI range pill
    all_same_roi = (
        fs.roi_range[0] == round(df_full["ROI_Pct"].min(), 1)
        and fs.roi_range[1] == round(df_full["ROI_Pct"].max(), 1)
    )
    roi_label = "All ROI" if all_same_roi else f'{fs.roi_range[0]:.0f}%–{fs.roi_range[1]:.0f}%'
    pills.append(
        f'<span class="fs-pill" style="background:#F0EEFF;color:#5B3BB5">'
        f'📈 {roi_label}</span>'
    )

    pills_html = " ".join(pills)

    count_color = "#2ECC71" if not is_filtered else "#1E6FBA"

    st.markdown(
        f"""
        <div class="filter-summary">
            <span class="fs-label">Active filters</span>
            {pills_html}
            <span class="fs-count" style="color:{count_color}">
                {n_shown} / {n_total} clients
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )