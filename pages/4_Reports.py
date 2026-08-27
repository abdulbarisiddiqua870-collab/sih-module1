"""
LEGALMETRIX - MODULE 3
Reports page - generate and download a PDF for any stored inspection.
"""

import streamlit as st

import config
from database.db import init_db, get_all_inspections
from services.pdf_service import generate_pdf, PDFGenerationError
from ui.components import inject_global_css, demo_mode_badge, render_brand_header, render_pipeline, status_badge

st.set_page_config(page_title=f"Reports \u2013 {config.APP_NAME}", page_icon="\U0001f4c4", layout="wide")
inject_global_css()
init_db()

render_brand_header("Inspection Reports", "Generate an auditable PDF summary for every stored inspection.")
demo_mode_badge()
st.caption("Every report carries the mandatory preliminary-screening disclaimer and never states "
           "a final legal determination.")
render_pipeline()

records = get_all_inspections()
if not records:
    st.info("No inspections available yet.")
    st.stop()

for r in records:
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([1.5, 2.5, 1, 1.2, 1.5])
        col1.caption("INSPECTION")
        col1.markdown(f"**{r['inspection_id']}**")
        col2.caption("PRODUCT")
        col2.write(r["product"].get("name") or "Unknown product")
        col3.caption("SCORE")
        col3.write(r["assessment"].get("score", "N/A"))
        col4.caption("STATUS")
        with col4:
            status_badge(r["assessment"].get("status", "-"))
        with col5:
            try:
                if st.button("Prepare PDF", key=f"gen_{r['inspection_id']}", type="primary"):
                    path = generate_pdf(r)
                    st.session_state[f"report_path_{r['inspection_id']}"] = path
            except PDFGenerationError as exc:
                st.error(str(exc))

            path = st.session_state.get(f"report_path_{r['inspection_id']}")
            if path:
                with open(path, "rb") as f:
                    st.download_button(
                        "Download PDF", data=f.read(),
                        file_name=f"{r['inspection_id']}_report.pdf",
                        mime="application/pdf",
                        key=f"dl2_{r['inspection_id']}",
                    )
