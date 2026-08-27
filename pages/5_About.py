"""
LEGALMETRIX - MODULE 3
About page.
"""

import streamlit as st

import config
from ui.components import inject_global_css, demo_mode_badge, render_brand_header, render_pipeline

st.set_page_config(page_title=f"About \u2013 {config.APP_NAME}", page_icon="\u2139\ufe0f", layout="wide")
inject_global_css()

render_brand_header("About ComplyAI", "A transparent three-module workflow for AI-assisted product verification.")
demo_mode_badge()
render_pipeline()

st.markdown(f"""
**Project:** {config.PROJECT_CODE} \u2014 Software System to Check Compliance of Packaged
Commodities under the Legal Metrology (Packaged Commodities) Rules, 2011.

**ComplyAI is Module 3 of a three-module system.**
""")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("#### Module 1")
    st.caption("Owned by teammates")
    st.write("OCR + product field extraction from the package image. "
             "Outputs structured product information.")
with col2:
    st.markdown("#### Module 2")
    st.caption("Owned by teammates")
    st.write("Legal Metrology compliance decision engine: validation, consistency checks, "
             "decision, score, findings, and confidence. Outputs a structured compliance "
             "decision JSON.")
with col3:
    st.markdown("#### Module 3 \u2014 this app")
    st.caption("LEGALMETRIX")
    st.write("Dashboard, history, analytics, evidence presentation, and inspection reports "
             "on top of Module 2's decision.")

st.divider()
st.markdown("#### What Module 3 does **not** do")
st.write(
    "- Does not perform OCR or image recognition.\n"
    "- Does not implement Legal Metrology rules.\n"
    "- Does not independently decide whether a product is compliant.\n"
    "- Never states a final legal determination \u2014 only Module 2's preliminary output."
)

st.divider()
st.markdown(f"#### {config.DISCLAIMER_TITLE}")
st.info(config.DISCLAIMER_TEXT)

st.divider()
st.markdown("#### Technology")
st.write("Streamlit \u00b7 SQLite \u00b7 ReportLab \u00b7 Plotly \u00b7 Requests")
st.caption(f"MOCK_MODE is currently **{config.MOCK_MODE}**. "
           f"Module 2 endpoint: `{config.MODULE2_INSPECT_ENDPOINT}`")
