"""ComplyAI Module 3 home dashboard."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

import config
from database.db import init_db, seed_if_empty, get_all_inspections
from services.analytics import compute_dashboard_stats
from ui.components import inject_global_css, demo_mode_badge, render_brand_header, render_kpis, render_pipeline

st.set_page_config(page_title="ComplyAI | Smart Product Verification", page_icon="C", layout="wide")
inject_global_css()
init_db()
seed_if_empty()

render_brand_header("Smart Product Verification", "AI-powered Legal Metrology inspection assistant")
demo_mode_badge()
render_pipeline()

records = get_all_inspections()
if not records:
    st.info("No inspections yet. Open **New Inspection** to run your first inspection.")
    st.stop()

stats = compute_dashboard_stats(records)
render_kpis([
    {"label": "Total Inspections", "value": stats["total"], "accent": "#1769aa"},
    {"label": "Average Compliance Score", "value": f'{stats["avg_score"]} / 100' if stats["avg_score"] is not None else "N/A", "accent": "#1769aa"},
    {"label": "Compliant", "value": stats["pass_count"], "accent": config.STATUS_COLORS[config.STATUS_PASS]},
    {"label": "Needs Review", "value": stats["review_count"] + stats["high_priority_count"], "accent": config.STATUS_COLORS[config.STATUS_REVIEW]},
])

st.write("")
left, right = st.columns([1.15, 1])
with left:
    with st.container(border=True):
        st.markdown("#### Compliance Status Distribution")
        status_counts = stats["status_counts"]
        fig = go.Figure(data=[go.Pie(labels=list(status_counts), values=list(status_counts.values()), hole=.62, marker_colors=[config.STATUS_COLORS.get(s, "#60758a") for s in status_counts])])
        fig.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-.08))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
with right:
    with st.container(border=True):
        st.markdown("#### Recent Inspections")
        rows = [{"Inspection ID": r["inspection_id"], "Product": r["product"].get("name"), "Score": r["assessment"].get("score"), "Status": r["assessment"].get("status")} for r in records[:8]]
        st.dataframe(rows, use_container_width=True, hide_index=True, height=300)
        st.caption("Open Inspection History to search and view full inspection evidence.")

st.write("")
with st.container(border=True):
    st.markdown("#### Score Distribution")
    scores = [r["assessment"]["score"] for r in records if r["assessment"].get("score") is not None]
    if scores:
        fig = px.histogram(x=scores, nbins=10, labels={"x": "Compliance score", "y": "Inspections"}, color_discrete_sequence=["#1769aa"])
        fig.update_layout(height=270, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("No score data available.")
