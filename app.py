import streamlit as st
import pandas as pd
import plotly.express as px

from utils.data_loader import load_portfolio
from utils.kpi_cards import compute_kpis, render_kpi_row
from charts_section import render_charts_section
from utils.sidebar_filters import render_sidebar, apply_filters, render_filter_summary
from utils.recommendation_engine import (
    generate_recommendations,
    render_recommendations
)

st.set_page_config(
    page_title="WIN Advisors Dashboard",
    page_icon="💼",
    layout="wide"
)

st.title("WIN Advisors — Portfolio Dashboard")
st.caption("Client portfolio analytics and insights")

df_full = load_portfolio()

filter_state = render_sidebar(df_full)
df = apply_filters(df_full, filter_state)

render_filter_summary(df_full, df, filter_state)

kpis = compute_kpis(df)
render_kpi_row(kpis)

render_charts_section(df)

recommendations = generate_recommendations(df)
render_recommendations(recommendations)

st.success(f"Loaded {len(df)} client records")
st.dataframe(df.head(10))