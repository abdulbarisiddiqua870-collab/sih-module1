"""
LEGALMETRIX - MODULE 3
Inspection History page.
"""

import streamlit as st

import config
from database.db import init_db, get_all_inspections, get_inspection
from services.pdf_service import generate_pdf, PDFGenerationError
from ui.components import inject_global_css, demo_mode_badge, render_full_inspection, render_brand_header, render_pipeline

st.set_page_config(page_title=f"History \u2013 {config.APP_NAME}", page_icon="\U0001f4dc", layout="wide")
inject_global_css()
init_db()

render_brand_header("Inspection History", "Search, filter, and reopen every inspection captured by ComplyAI.")
demo_mode_badge()
render_pipeline()

records = get_all_inspections()

if not records:
    st.info("No inspections stored yet. Run one from **New Inspection** first.")
    st.stop()

filter_col1, filter_col2, filter_col3 = st.columns([2, 1.4, 1.2])
with filter_col1:
    search = st.text_input("Search by product name or inspection ID", "")
with filter_col2:
    status_filter = st.multiselect(
        "Filter by status",
        options=[config.STATUS_PASS, config.STATUS_REVIEW, config.STATUS_HIGH_PRIORITY],
        default=[],
    )
with filter_col3:
    sort_by = st.selectbox("Sort by", ["Newest first", "Oldest first", "Highest score", "Lowest score"])

filtered = records
if search.strip():
    q = search.strip().lower()
    filtered = [
        r for r in filtered
        if q in (r["product"].get("name") or "").lower() or q in r["inspection_id"].lower()
    ]
if status_filter:
    filtered = [r for r in filtered if r["assessment"].get("status") in status_filter]

if sort_by == "Newest first":
    filtered = sorted(filtered, key=lambda r: r["timestamp"], reverse=True)
elif sort_by == "Oldest first":
    filtered = sorted(filtered, key=lambda r: r["timestamp"])
elif sort_by == "Highest score":
    filtered = sorted(filtered, key=lambda r: (r["assessment"].get("score") or 0), reverse=True)
elif sort_by == "Lowest score":
    filtered = sorted(filtered, key=lambda r: (r["assessment"].get("score") or 0))

st.caption(f"Showing {len(filtered)} of {len(records)} inspections.")

table_rows = [{
    "Inspection ID": r["inspection_id"],
    "Timestamp": r["timestamp"],
    "Product": r["product"].get("name"),
    "Score": r["assessment"].get("score"),
    "Status": r["assessment"].get("status"),
    "Findings": r.get("finding_count", 0),
} for r in filtered]
st.dataframe(table_rows, use_container_width=True, hide_index=True)

st.divider()
st.markdown("### Open an Inspection")
options = [r["inspection_id"] for r in filtered]
if options:
    selected_id = st.selectbox("Select an inspection to view its full result", options)
    inspection = get_inspection(selected_id)

    if inspection:
        render_full_inspection(inspection)

        st.write("")
        try:
            if st.button("\U0001f4c4 Prepare PDF Report", key=f"pdf_{selected_id}"):
                path = generate_pdf(inspection)
                st.session_state[f"pdf_path_{selected_id}"] = path
        except PDFGenerationError as exc:
            st.error(str(exc))

        ready_path = st.session_state.get(f"pdf_path_{selected_id}")
        if ready_path:
            with open(ready_path, "rb") as f:
                st.download_button(
                    "\u2b07\ufe0f Download Inspection Report (PDF)",
                    data=f.read(),
                    file_name=f"{inspection['inspection_id']}_report.pdf",
                    mime="application/pdf",
                    key=f"dl_{selected_id}",
                )
else:
    st.caption("No inspections match your filters.")
