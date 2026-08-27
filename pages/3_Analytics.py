"""
LEGALMETRIX - MODULE 3
Analytics page.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

import config
from database.db import init_db, get_all_inspections, has_demo_data
from services.analytics import compute_full_analytics
from ui.components import inject_global_css, demo_mode_badge, render_brand_header, render_pipeline, render_kpis

st.set_page_config(page_title=f"Analytics \u2013 {config.APP_NAME}", page_icon="\U0001f4ca", layout="wide")
inject_global_css()
init_db()

render_brand_header("Inspection Analytics", "A factual view of the compliance decisions already returned by Module 2.")
demo_mode_badge()
render_pipeline()

records = get_all_inspections()
if not records:
    st.info("No inspection data yet.")
    st.stop()

if has_demo_data():
    st.markdown(
        '<span class="lm-demo-badge">Includes seeded DEMO DATA \u2014 not real inspection outcomes</span>',
        unsafe_allow_html=True,
    )

st.divider()

analytics = compute_full_analytics(records)

render_kpis([
    {"label": "Total Inspections", "value": analytics["total"], "accent": "#1769aa"},
    {"label": "Average Score", "value": analytics["avg_score"] if analytics["avg_score"] is not None else "N/A", "accent": "#1769aa"},
    {"label": "PASS", "value": f'{analytics["pass_pct"]}%', "accent": config.STATUS_COLORS[config.STATUS_PASS]},
    {"label": "REVIEW", "value": f'{analytics["review_pct"]}%', "accent": config.STATUS_COLORS[config.STATUS_REVIEW]},
    {"label": "HIGH PRIORITY", "value": f'{analytics["high_priority_pct"]}%', "accent": config.STATUS_COLORS[config.STATUS_HIGH_PRIORITY]},
])

st.write("")
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### Compliance Distribution")
    status_counts = analytics["status_counts"]
    if status_counts:
        fig = go.Figure(data=[go.Pie(
            labels=list(status_counts.keys()), values=list(status_counts.values()),
            hole=0.5, marker_colors=[config.STATUS_COLORS.get(s, "#999") for s in status_counts.keys()],
        )])
        fig.update_layout(height=340, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("#### Most Common Findings")
    categories = analytics["violation_categories"]
    if categories:
        fig = px.bar(x=list(categories.values()), y=list(categories.keys()), orientation="h",
                     labels={"x": "Occurrences", "y": ""}, color_discrete_sequence=["#C0392B"])
        fig.update_layout(height=340, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("No recurring violation categories found.")

st.markdown("#### Inspection Trend")
trend = analytics["trend"]
if trend:
    timestamps, scores = zip(*trend)
    fig = px.line(x=timestamps, y=scores, markers=True,
                  labels={"x": "Timestamp", "y": "Compliance Score"},
                  color_discrete_sequence=["#1B3A6B"])
    fig.update_layout(height=340, margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Not enough data for a trend line yet.")
