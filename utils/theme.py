"""
utils/theme.py
==============
Design-token hub and reusable HTML/CSS component library
for the WIN Advisors Enterprise Dashboard.

WHAT THIS FILE PROVIDES
────────────────────────
  inject_global_theme()   → call once at top of app.py; loads fonts +
                            Google Icons + all base CSS variables
  section_header()        → consistent section divider with icon + title
  divider()               → subtle hr between sections
  card_open/close         → HTML wrappers that give a chart/block a card look
  skeleton_kpi_row()      → CSS-shimmer loading placeholder for KPI row
  skeleton_chart()        → CSS-shimmer loading placeholder for a chart
  stat_delta()            → coloured delta pill (▲ +3.5%)
  info_badge()            → small coloured pill with icon + text
  metric_footnote()       → tiny grey text beneath a section

All HTML is self-contained (no external dependencies beyond the CSS
already loaded in style.css) and safe to pass to
st.markdown(..., unsafe_allow_html=True).
"""

import streamlit as st
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
#  GLOBAL THEME INJECTOR
# ─────────────────────────────────────────────────────────────────────────────

def inject_global_theme() -> None:
    """
    Call this ONCE at the very top of app.py, right after set_page_config().

    What it injects:
      1. Google Fonts (DM Sans 300–800, DM Mono 400–500)
      2. Material Symbols icon font
      3. CSS reset / base layer (supplements style.css)
      4. Streamlit-specific utility overrides

    Usage in app.py:
        from utils.theme import inject_global_theme
        inject_global_theme()          # ← line 1 after set_page_config
    """
    # Load fonts + icon font
    st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800;1,9..40,400&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

    # Extra CSS supplements (animation keyframes, print styles)
    st.markdown("""
    <style>
    /* ── Fade-in for main content on load ─────────────────── */
    .main .block-container {
        animation: win-fadein 0.35s ease-out both;
    }
    @keyframes win-fadein {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0);   }
    }

    /* ── Stagger children inside columns ──────────────────── */
    div[data-testid="column"]:nth-child(1) { animation-delay: 0.00s; }
    div[data-testid="column"]:nth-child(2) { animation-delay: 0.04s; }
    div[data-testid="column"]:nth-child(3) { animation-delay: 0.08s; }
    div[data-testid="column"]:nth-child(4) { animation-delay: 0.12s; }
    div[data-testid="column"]:nth-child(5) { animation-delay: 0.16s; }

    /* ── Plotly chart container polish ────────────────────── */
    .stPlotlyChart > div {
        border-radius : 10px !important;
        overflow      : hidden;
    }
    /* Remove Plotly default white background bleed */
    .stPlotlyChart > div > div { background: transparent !important; }

    /* ── Expander polish ──────────────────────────────────── */
    details[data-testid="stExpander"] {
        border        : 1px solid #E4E8EE !important;
        border-radius : 12px !important;
        box-shadow    : 0 1px 3px rgba(10,35,66,0.05) !important;
        overflow      : hidden;
        background    : #FFFFFF;
    }
    details[data-testid="stExpander"] > summary {
        padding       : 12px 18px;
        background    : #FFFFFF;
        border-bottom : 1px solid #E4E8EE;
    }
    details[data-testid="stExpander"][open] > summary {
        border-bottom-color: #D0D6DF;
    }
    details[data-testid="stExpander"] .streamlit-expanderContent {
        padding: 16px 18px;
    }

    /* ── Radio buttons (used in rec filter) ─────────────────── */
    [data-testid="stRadio"] > label { display: none; }
    [data-testid="stRadio"] > div {
        display    : flex;
        gap        : 6px;
        flex-wrap  : wrap;
    }
    [data-testid="stRadio"] label[data-baseweb="radio"] {
        background   : #F0F2F6;
        border       : 1px solid #E4E8EE;
        border-radius: 20px;
        padding      : 4px 14px;
        cursor       : pointer;
        font-size    : 12px !important;
        font-weight  : 500;
        transition   : all 120ms ease;
        color        : #4A5568 !important;
    }
    [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        background: #E4E8EE;
        color     : #0F1923 !important;
    }
    [data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] {
        background  : #0A2342;
        border-color: #0A2342;
        color       : #FFFFFF !important;
    }
    /* Hide the radio input circle */
    [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
        display: none;
    }

    /* ── Tooltip / popover refinement ────────────────────── */
    [data-testid="stTooltipIcon"] { color: #8896A6; }

    /* ── Print: clean export ──────────────────────────────── */
    @media print {
        [data-testid="stSidebar"],
        [data-testid="stHeader"],
        .stButton { display: none !important; }
        .block-container { max-width: 100% !important; padding: 0 !important; }
        .company-header { border-radius: 0 !important; }
    }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  SECTION HEADERS
# ─────────────────────────────────────────────────────────────────────────────

def section_header(icon: str, title: str, subtitle: str = "") -> None:
    """
    Renders a premium section header with a left accent bar.

    Parameters
    ──────────
    icon     : Emoji or icon character shown left of title
    title    : Main heading text
    subtitle : Optional smaller text beneath the title

    Usage:
        section_header("", "KPI Overview", "Metrics for the filtered client set")
    """
    sub_html = (
        f'<div style="font-size:12px;color:#8896A6;'
        f'font-weight:400;margin-top:2px">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(f"""
    <div style="display:flex;align-items:flex-start;gap:10px;
                padding-left:14px;margin-bottom:18px;position:relative">
        <!-- Left accent gradient bar -->
        <div style="position:absolute;left:0;top:2px;bottom:2px;width:4px;
                    background:linear-gradient(180deg,#1E6FBA,#C9A84C);
                    border-radius:2px"></div>
        <span style="font-size:18px;line-height:1.1;flex-shrink:0;
                     margin-top:1px">{icon}</span>
        <div>
            <div style="font-size:15.5px;font-weight:700;color:#0F1923;
                        line-height:1.25;letter-spacing:-0.2px">{title}</div>
            {sub_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def divider(top: int = 28, bottom: int = 28) -> None:
    """
    Renders an elegant gradient divider between sections.
    Much nicer than plain st.divider() or <hr>.
    """
    st.markdown(f"""
    <div style="height:1px;
                background:linear-gradient(90deg,
                  transparent 0%,#E4E8EE 8%,#D0D6DF 50%,#E4E8EE 92%,transparent 100%);
                margin:{top}px 0 {bottom}px"></div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CARD WRAPPERS
# ─────────────────────────────────────────────────────────────────────────────

CARD_OPEN = """
<div style="background:#FFFFFF;border:1px solid #E4E8EE;border-radius:14px;
            padding:18px 16px 12px;
            box-shadow:0 1px 3px rgba(10,35,66,0.06),0 1px 2px rgba(10,35,66,0.04);
            transition:box-shadow 200ms ease">
"""
CARD_CLOSE = "</div>"


def card(content_fn, *args, **kwargs):
    """
    Context-manager-style wrapper.
    Usage:
        st.markdown(CARD_OPEN, unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(CARD_CLOSE, unsafe_allow_html=True)
    """
    st.markdown(CARD_OPEN, unsafe_allow_html=True)
    content_fn(*args, **kwargs)
    st.markdown(CARD_CLOSE, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  LOADING SKELETONS
# ─────────────────────────────────────────────────────────────────────────────

def skeleton_kpi_row(n: int = 5) -> None:
    """
    Renders N skeleton KPI cards as placeholders while data loads.
    Uses CSS shimmer animation from style.css.

    Usage:
        if not data_ready:
            skeleton_kpi_row(5)
        else:
            render_kpi_row(kpis)
    """
    cols = st.columns(n, gap="small")
    for col in cols:
        with col:
            st.markdown("""
            <div style="background:#FFFFFF;border:1px solid #E4E8EE;
                        border-top:3px solid #E4E8EE;border-radius:12px;
                        padding:20px 22px;min-height:152px">
                <div class="skeleton skeleton-title"
                     style="height:11px;width:55%;margin-bottom:14px;
                            border-radius:6px"></div>
                <div class="skeleton skeleton-value"
                     style="height:30px;width:65%;margin-bottom:10px;
                            border-radius:8px"></div>
                <div class="skeleton skeleton-text"
                     style="height:10px;width:80%;margin-bottom:7px;
                            border-radius:6px"></div>
                <div style="height:1px;background:#E4E8EE;margin:10px -4px"></div>
                <div class="skeleton skeleton-text-sm"
                     style="height:10px;width:45%;border-radius:6px"></div>
            </div>
            """, unsafe_allow_html=True)


def skeleton_chart(height: int = 320, label: str = "") -> None:
    """
    Renders a shimmer placeholder where a chart will appear.

    Usage:
        skeleton_chart(320, "Portfolio Performance")
    """
    lbl = f'<div style="font-size:11px;color:#8896A6;margin-bottom:10px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px">{label}</div>' if label else ""
    st.markdown(f"""
    <div style="background:#FFFFFF;border:1px solid #E4E8EE;border-radius:14px;
                padding:20px;box-shadow:0 1px 3px rgba(10,35,66,0.05)">
        {lbl}
        <div class="skeleton" style="height:{height}px;border-radius:10px"></div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  INLINE UI COMPONENTS
# ─────────────────────────────────────────────────────────────────────────────

def stat_delta(value: float, suffix: str = "%",
               good_if_positive: bool = True) -> str:
    """
    Returns an HTML string for a coloured delta pill.
    Positive and good → green ▲. Positive and bad → red ▲.

    Usage:
        st.markdown(stat_delta(3.5), unsafe_allow_html=True)
        → renders green  ▲ +3.5%

        st.markdown(stat_delta(-1.2), unsafe_allow_html=True)
        → renders red  ▼ −1.2%
    """
    is_positive = value >= 0
    is_good     = is_positive == good_if_positive

    color  = "#1AA054" if is_good else "#C53030"
    bg     = "rgba(26,160,84,0.10)" if is_good else "rgba(197,48,48,0.10)"
    arrow  = "▲" if is_positive else "▼"
    sign   = "+" if is_positive else ""

    return (
        f'<span style="display:inline-flex;align-items:center;gap:3px;'
        f'background:{bg};color:{color};font-size:11px;font-weight:700;'
        f'padding:2px 8px;border-radius:20px">'
        f'{arrow} {sign}{value:.1f}{suffix}</span>'
    )


def info_badge(text: str, kind: str = "info",
               icon: str = "") -> None:
    """
    Renders a small coloured insight badge (full-width block).

    Parameters
    ──────────
    text : Badge text
    kind : "info" | "success" | "warning" | "danger"
    icon : Leading emoji
    """
    styles = {
        "info"   : ("rgba(30,111,186,0.07)", "#1B54A0", "rgba(30,111,186,0.20)"),
        "success": ("rgba(26,160,84,0.07)",  "#16643A", "rgba(26,160,84,0.20)"),
        "warning": ("rgba(217,119,6,0.07)",  "#92580A", "rgba(217,119,6,0.20)"),
        "danger" : ("rgba(197,48,48,0.07)",  "#922B21", "rgba(197,48,48,0.20)"),
    }
    bg, fg, border_color = styles.get(kind, styles["info"])
    st.markdown(
        f'<div style="background:{bg};border:1px solid {border_color};'
        f'border-radius:8px;padding:7px 13px;font-size:12px;color:{fg};'
        f'font-weight:500;line-height:1.5;margin-top:7px;display:flex;'
        f'align-items:flex-start;gap:7px">'
        f'<span style="flex-shrink:0">{icon}</span><span>{text}</span></div>',
        unsafe_allow_html=True,
    )


def metric_footnote(text: str) -> None:
    """Renders a small grey footnote beneath a metric or section."""
    st.markdown(
        f'<div style="font-size:11px;color:#8896A6;margin-top:5px;'
        f'line-height:1.5">{text}</div>',
        unsafe_allow_html=True,
    )


def page_footer() -> None:
    """Renders the consistent bottom footer."""
    now_year = datetime.now().year
    st.markdown(f"""
    <div style="text-align:center;padding:24px 0 8px;
                color:#A8B5C2;font-size:11.5px;
                border-top:1px solid #E4E8EE;margin-top:40px">
        <span style="font-weight:600;color:#6B7280">WIN ADVISORS</span>
        &nbsp;·&nbsp; Portfolio Intelligence Platform
        &nbsp;·&nbsp; Python · Streamlit · Pandas · Plotly
        &nbsp;·&nbsp; © {now_year} &nbsp;
        <span style="color:#C9A84C">Internal Use Only</span>
    </div>
    """, unsafe_allow_html=True)