"""ComplyAI Module 3 new inspection workflow."""

import streamlit as st

import config
from database.db import init_db, insert_inspection
from services.module2_client import get_inspection, Module2Error
from services.pdf_service import generate_pdf, PDFGenerationError
from ui.components import inject_global_css, demo_mode_badge, render_full_inspection, render_brand_header, render_pipeline

st.set_page_config(page_title=f"New Inspection - {config.APP_NAME}", page_icon="C", layout="wide")
inject_global_css()
init_db()

render_brand_header("New Inspection", "Upload a product label image, then review the structured compliance decision.")
demo_mode_badge()
render_pipeline()

st.markdown("### Start with a product image")
st.caption("Module 1 performs OCR and field extraction. Module 2 evaluates the extracted declarations. This dashboard presents the resulting inspection report.")
uploaded = st.file_uploader("Upload product label image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
if uploaded:
    st.image(uploaded, caption="Source image", width=320)
    st.info("Image preview loaded. Connect the Module 1 extraction output in Advanced / Integration Testing to continue without changing the existing API contract.")

with st.expander("Advanced / Integration Testing", expanded=False):
    tab_mock, tab_paste, tab_live = st.tabs(["Generate demo result", "Paste Module 2 JSON", "Call live Module 2 API"])

    with tab_mock:
        st.write("Load a simulated Module 2 result for an offline demo.")
        if st.button("Generate Mock Inspection", type="primary"):
            try:
                inspection = get_inspection(mode="mock")
                insert_inspection(inspection, is_demo=False)
                st.session_state["current_inspection"] = inspection
                st.success(f"Loaded inspection {inspection['inspection_id']}.")
            except Module2Error as exc:
                st.error(str(exc))

    with tab_paste:
        st.write("Paste a raw Module 2 JSON response to test the report renderer.")
        json_text = st.text_area("Module 2 JSON response", height=220, placeholder='{"inspection_id": "...", "product": {...}, "assessment": {...}, ...}')
        if st.button("Load JSON"):
            try:
                inspection = get_inspection(mode="paste", raw_json_text=json_text)
                insert_inspection(inspection, is_demo=False)
                st.session_state["current_inspection"] = inspection
                st.success(f"Loaded inspection {inspection['inspection_id']}.")
            except Module2Error as exc:
                st.error(str(exc))

    with tab_live:
        if config.MOCK_MODE:
            st.warning("MOCK_MODE is currently true, so this returns simulated data. Set MOCK_MODE=false to call the configured Module 2 service.")
        else:
            st.write(f"Live Module 1 ProductData will be sent to `{config.MODULE2_INSPECT_ENDPOINT}`.")
        payload_text = st.text_area("Module 1 ProductData JSON", height=220, placeholder='{"product_name":{"value":"ABC Biscuits","confidence":0.95},"mrp":{"value":"₹50","confidence":0.96},...}')
        if st.button("Call Module 2"):
            import json
            try:
                payload = json.loads(payload_text) if payload_text.strip() else {}
            except json.JSONDecodeError as exc:
                st.error(f"Payload is not valid JSON ({exc.msg}).")
                payload = None
            if payload is not None:
                try:
                    inspection = get_inspection(mode="live", payload=payload)
                    insert_inspection(inspection, is_demo=False)
                    st.session_state["current_inspection"] = inspection
                    st.success(f"Loaded inspection {inspection['inspection_id']}.")
                except Module2Error as exc:
                    st.error(str(exc))

st.divider()
inspection = st.session_state.get("current_inspection")
if inspection:
    st.markdown("### Inspection Report")
    render_full_inspection(inspection)
    try:
        if st.button("Prepare PDF Report", type="primary"):
            st.session_state["current_pdf_path"] = generate_pdf(inspection)
    except PDFGenerationError as exc:
        st.error(str(exc))
    ready_path = st.session_state.get("current_pdf_path")
    if ready_path:
        with open(ready_path, "rb") as f:
            st.download_button("Download Inspection Report (PDF)", data=f.read(), file_name=f"{inspection['inspection_id']}_report.pdf", mime="application/pdf")
else:
    st.info("No inspection loaded yet. Upload an image or open Advanced / Integration Testing.")
