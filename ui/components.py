"""
Shared Streamlit rendering components.

Every page that needs to show a full inspection result (New Inspection,
Inspection History) uses these functions so the presentation stays
consistent across the app.
"""

import os

import streamlit as st

import config


def inject_global_css():
    st.markdown(
        """
        <style>
        :root { --lm-navy: #102a43; --lm-blue: #1769aa; --lm-ink: #17324d; --lm-muted: #60758a; --lm-border: #dce6ef; }
        .block-container { max-width: 1440px; padding-top: 2.2rem; padding-bottom: 4rem; }
        [data-testid="stSidebar"] { background: #102a43; }
        [data-testid="stSidebar"] * { color: #e8f1f8; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #b9cde0; }
        h1, h2, h3, h4 { color: #102a43; letter-spacing: -0.02em; }
        .lm-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.78rem;
            letter-spacing: 0.03em;
            color: white;
        }

        .lm-demo-badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 6px;
            background: #FFF3CD;
            color: #7A5A00;
            font-weight: 600;
            font-size: 0.75rem;
            border: 1px solid #F5D98B;
        }

        .lm-card {
            background: white;
            border-radius: 14px;
            padding: 22px 24px;
            border: 1px solid #E4E8EE;
            box-shadow: 0 4px 18px rgba(16,42,67,0.06);
        }

        .lm-hero { background: linear-gradient(120deg, #102a43 0%, #1769aa 100%); color: white; border-radius: 18px; padding: 30px 34px; margin-bottom: 24px; box-shadow: 0 12px 28px rgba(16,42,67,.18); }
        .lm-hero h1 { color: white; font-size: 2.25rem; margin: 0 0 4px; }
        .lm-hero p { color: #d8e8f4; margin: 0; font-size: 1rem; }
        .lm-eyebrow { color: #83c5ed; text-transform: uppercase; letter-spacing: .12em; font-size: .72rem; font-weight: 800; margin-bottom: 9px; }
        .lm-kpi { background: #fff; border: 1px solid var(--lm-border); border-radius: 14px; padding: 19px 20px; min-height: 112px; box-shadow: 0 3px 14px rgba(16,42,67,.05); border-top: 4px solid var(--accent); }
        .lm-kpi-label { color: var(--lm-muted); font-size: .76rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
        .lm-kpi-value { color: var(--lm-ink); font-size: 2rem; font-weight: 800; margin-top: 9px; }
        .lm-pipeline { display:flex; flex-wrap:wrap; align-items:center; gap: 8px; background:#eef6fb; border:1px solid #d5e8f5; border-radius:12px; padding:14px 18px; color:var(--lm-ink); font-size:.88rem; font-weight:700; margin: 10px 0 24px; }
        .lm-pipeline span { color:var(--lm-blue); }
        .lm-result-head { background:#f6f9fc; border:1px solid var(--lm-border); border-radius:14px; padding:20px 24px; margin-bottom:18px; }
        .lm-result-head h2 { margin:0 0 4px; }
        .lm-section-title { font-size: 1.08rem; font-weight: 800; color: #102a43; margin: 0 0 10px 0; }
        .lm-explanation { background: #f3f8fc; border: 1px solid #cfe2ef; border-left: 5px solid #1769aa; border-radius: 14px; padding: 20px 23px; }
        .lm-explanation h3 { margin-top:0; font-size:1.05rem; }

        .lm-score {
            font-size: 2.6rem;
            font-weight: 800;
            color: #1B3A6B;
            line-height: 1;
        }

        .lm-subtle {
            color: #6B7280;
            font-size: 0.85rem;
        }

        .lm-section-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #1B3A6B;
            margin: 0 0 8px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def demo_mode_badge():
    if config.MOCK_MODE:
        st.markdown(
            '<span class="lm-demo-badge">DEMO MODE &mdash; MOCK_MODE=true</span>',
            unsafe_allow_html=True,
        )


def status_badge(status: str):
    color = config.STATUS_COLORS.get(status, "#555555")

    st.markdown(
        f'<span class="lm-badge" style="background:{color};">{status}</span>',
        unsafe_allow_html=True,
    )


def render_brand_header(page_title=None, description=None):
    title = page_title or "Smart Product Verification"
    copy = description or "AI-powered Legal Metrology inspection assistant"
    st.markdown(
        f'<div class="lm-hero"><div class="lm-eyebrow">ComplyAI &nbsp; / &nbsp; Inspection platform</div>'
        f'<h1>{title}</h1><p>{copy}</p></div>', unsafe_allow_html=True)


def render_pipeline():
    st.markdown('<div class="lm-pipeline"><span>Image</span> &rarr; <span>OCR &amp; Extraction</span> &rarr; <span>Compliance Engine</span> &rarr; <span>Inspection Report</span></div>', unsafe_allow_html=True)


def render_kpis(items):
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            st.markdown(
                f'<div class="lm-kpi" style="--accent:{item["accent"]}"><div class="lm-kpi-label">{item["label"]}</div><div class="lm-kpi-value">{item["value"]}</div></div>',
                unsafe_allow_html=True,
            )


def render_score_card(inspection: dict):
    assessment = inspection.get("assessment", {})

    score = assessment.get("score")
    status = assessment.get("status", "REVIEW")
    confidence = assessment.get("confidence")

    product_name = inspection.get("product", {}).get("name") or "Unknown product"
    st.markdown(f'<div class="lm-result-head"><div class="lm-eyebrow">Inspection result</div><h2>{product_name}</h2><span class="lm-subtle">{inspection.get("inspection_id", "-")} &nbsp;|&nbsp; {inspection.get("timestamp", "-")}</span></div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1.1, 1, 1, 1])

    with col1:
        st.markdown(
            '<div class="lm-card">',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="lm-subtle">COMPLIANCE SCORE</div>',
            unsafe_allow_html=True,
        )

        score_display = score if score is not None else "N/A"

        st.markdown(
            f'<div class="lm-score">{score_display}'
            f'<span style="font-size:1.1rem;color:#6B7280;"> / 100</span></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            '<div class="lm-card">',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="lm-subtle">STATUS</div>',
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        status_badge(status)

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            '<div class="lm-card">',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="lm-subtle">AI CONFIDENCE</div>',
            unsafe_allow_html=True,
        )

        conf_display = f"{round(confidence * 100)}%" if confidence is not None else "N/A"
        st.markdown(f'<div style="font-size:1.6rem;font-weight:700;">{conf_display}</div></div>', unsafe_allow_html=True)

    with col4:
        requirements = assessment_requirements(inspection)
        verified = sum(1 for item in requirements if item.get("status") == config.STATUS_PASS)
        total = len(requirements)
        st.markdown('<div class="lm-card"><div class="lm-subtle">DECLARATIONS VERIFIED</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:1.6rem;font-weight:700;">{verified} <span style="font-size:.95rem;color:#6B7280;">/ {total}</span></div></div>', unsafe_allow_html=True)


def assessment_requirements(inspection):
    return inspection.get("requirements", [])


def render_product_info(inspection: dict):
    product = inspection.get("product", {})

    st.markdown(
        '<div class="lm-section-title">Product Information</div>',
        unsafe_allow_html=True,
    )

    labels = [
        ("Product name", "name"),
        ("Brand", "brand"),
        ("Manufacturer", "manufacturer"),
        ("Manufacturer address", "manufacturer_address"),
        ("Packer", "packer"),
        ("Importer", "importer"),
        ("Net quantity", "net_quantity"),
        ("MRP", "mrp"),
        ("Manufacture date", "manufacture_date"),
        ("Pack date", "pack_date"),
        ("Consumer care", "consumer_care"),
        ("Country of origin", "country_of_origin"),
    ]

    cols = st.columns(3)

    for i, (label, key) in enumerate(labels):
        value = product.get(key)

        with cols[i % 3]:
            display_value = (
                value
                if value
                else '<span style="color:#B0453B;">Not detected</span>'
            )

            st.markdown(
                f'<div class="lm-subtle">{label}</div>'
                f'<div style="margin-bottom:10px;font-weight:600;">'
                f'{display_value}'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_requirement_table(inspection: dict):
    requirements = inspection.get("requirements", [])

    st.markdown(
        '<div class="lm-section-title">Declaration Verification</div>',
        unsafe_allow_html=True,
    )

    if not requirements:
        st.info(
            "No requirement-level data was provided by Module 2."
        )
        return

    icon_map = {
        "PASS": "\u2705",
        "REVIEW": "\u26a0\ufe0f",
        "HIGH PRIORITY": "\u274c",
        "FAIL": "\u274c",
    }

    rows = []

    for requirement in requirements:
        conf = requirement.get("confidence")
        status = requirement.get("status", "REVIEW")

        if conf is not None:
            confidence_display = f"{round(conf * 100)}%"
        else:
            confidence_display = "N/A"

        rows.append(
            {
                "Field": requirement.get("name", "Unknown"),
                "Status": f"{icon_map.get(status, '')} {status}",
                "Value": (
                    requirement.get("detected_value")
                    or "Not detected"
                ),
                "Confidence": confidence_display,
            }
        )

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )


def render_findings(inspection: dict):
    findings = inspection.get("findings", [])

    st.markdown(
        '<div class="lm-section-title">Findings</div>',
        unsafe_allow_html=True,
    )

    if not findings:
        st.success(
            "No findings were raised for this inspection."
        )
        return

    for i, finding in enumerate(findings):
        severity = finding.get("severity", "MEDIUM")

        severity_color = config.SEVERITY_COLORS.get(
            severity,
            "#C77700",
        )

        confidence = finding.get("confidence")

        title = (
            finding.get("type", "FINDING")
            .replace("_", " ")
            .title()
        )

        with st.expander(
            f"{severity} — {title}",
            expanded=(i == 0),
        ):
            if confidence is not None:
                confidence_display = (
                    f"{round(confidence * 100)}%"
                )
            else:
                confidence_display = "N/A"

            st.markdown(
                f'<span class="lm-badge" '
                f'style="background:{severity_color};">'
                f'{severity} SEVERITY'
                f'</span> '
                f'&nbsp;&nbsp;'
                f'<span class="lm-subtle">'
                f'Confidence: {confidence_display}'
                f'</span>',
                unsafe_allow_html=True,
            )

            st.write("")

            st.markdown(
                f"**Detected field:** "
                f"{finding.get('field') or 'Not specified'}"
            )

            detected_value = finding.get("detected_value")

            if detected_value:
                detected_display = detected_value
            else:
                detected_display = "Not detected"

            st.markdown(
                f"**Detected value:** {detected_display}"
            )

            st.markdown(
                f"**Explanation:**  \n"
                f"{finding.get('explanation') or 'No explanation provided.'}"
            )

            st.markdown(
                f"**Recommended action:**  \n"
                f"{finding.get('recommended_action') or 'Manual verification recommended.'}"
            )


def render_decision_explanation(inspection: dict):
    assessment = inspection.get("assessment", {})
    findings = inspection.get("findings", [])
    status = assessment.get("status", config.STATUS_REVIEW)
    if findings:
        reasons = " ".join(f.get("explanation") for f in findings if f.get("explanation"))
        uncertain = ", ".join(f.get("field") for f in findings if f.get("field"))
        action = findings[0].get("recommended_action") or "Manual verification recommended."
    else:
        reasons = "No findings were raised by the compliance engine."
        uncertain = "None recorded"
        action = "Retain the report with the inspection record."
    st.markdown(
        f'<div class="lm-explanation"><h3>AI Decision Explanation</h3>'
        f'<p><b>Why this status:</b> {reasons or "No explanation provided by Module 2."}</p>'
        f'<p><b>Missing or uncertain declarations:</b> {uncertain or "None recorded"}</p>'
        f'<p><b>Recommended inspector action:</b> {action}</p></div>', unsafe_allow_html=True)


def render_evidence(inspection: dict):
    evidence = inspection.get("evidence", [])

    st.markdown(
        '<div class="lm-section-title">Evidence</div>',
        unsafe_allow_html=True,
    )

    if not evidence:
        st.caption("No visual evidence attached.")
        return

    for evidence_item in evidence:
        shown = False

        image_url = evidence_item.get("image_url")

        if image_url:
            try:
                st.image(
                    image_url,
                    use_container_width=True,
                )
                shown = True
            except Exception:
                pass

        elif (
            evidence_item.get("image_path")
            and os.path.exists(evidence_item["image_path"])
        ):
            st.image(
                evidence_item["image_path"],
                use_container_width=True,
            )
            shown = True

        if evidence_item.get("bbox"):
            st.caption(
                f"Bounding box: {evidence_item['bbox']}"
            )

        if evidence_item.get("description"):
            st.caption(
                evidence_item["description"]
            )

        elif (
            not shown
            and not evidence_item.get("bbox")
        ):
            st.caption(
                "Evidence reference provided without a viewable image."
            )


def render_warnings(inspection: dict):
    warnings = inspection.get("warnings", [])

    if warnings:
        with st.expander(
            "Normalization notes (data quality)",
            expanded=False,
        ):
            for warning in warnings:
                st.caption(
                    f"\u2022 {warning}"
                )


def render_full_inspection(inspection: dict):
    render_score_card(inspection)

    st.write("")

    render_product_info(inspection)

    st.divider()

    render_requirement_table(inspection)

    st.write("")
    render_decision_explanation(inspection)

    st.divider()

    render_findings(inspection)

    st.divider()

    render_evidence(inspection)

    render_warnings(inspection)
