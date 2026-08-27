"""
PDF inspection report generation.

Produces a professional, government/enterprise-style PDF report from a
normalized inspection dict. This module never makes a compliance
determination - it only presents what Module 2 already decided, and
always carries the mandatory preliminary-screening disclaimer.
"""

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

import config


class PDFGenerationError(Exception):
    pass


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AppTitle", fontSize=20, leading=24, textColor=colors.HexColor("#1B3A6B"),
        spaceAfter=2, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="AppSubtitle", fontSize=10, textColor=colors.HexColor("#555555"),
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", fontSize=13, textColor=colors.HexColor("#1B3A6B"),
        spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="Body", fontSize=9.5, leading=13,
    ))
    styles.add(ParagraphStyle(
        name="Disclaimer", fontSize=8.5, leading=12, textColor=colors.HexColor("#7A2E2E"),
    ))
    return styles


def _status_color(status):
    return colors.HexColor(config.STATUS_COLORS.get(status, "#555555"))


def _fmt(value, fallback="Not detected"):
    if value in (None, "", "null"):
        return fallback
    return str(value)


def _fmt_pct(value):
    if value is None:
        return "N/A"
    return f"{round(value * 100)}%"


def generate_pdf(inspection: dict) -> str:
    """
    Build the PDF report for `inspection` (a normalized inspection dict)
    and return the absolute file path it was written to.
    """
    try:
        styles = _styles()
        filename = f"{inspection['inspection_id']}.pdf"
        filepath = os.path.join(config.REPORTS_DIR, filename)

        doc = SimpleDocTemplate(
            filepath, pagesize=A4,
            leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=16 * mm, bottomMargin=16 * mm,
            title=f"{config.APP_NAME} Inspection Report - {inspection['inspection_id']}",
        )

        story = []
        product = inspection.get("product", {})
        assessment = inspection.get("assessment", {})
        status = assessment.get("status", "REVIEW")

        # Header
        story.append(Paragraph(config.APP_NAME, styles["AppTitle"]))
        story.append(Paragraph(config.APP_SUBTITLE, styles["AppSubtitle"]))
        story.append(HRFlowable(width="100%", color=colors.HexColor("#1B3A6B"), thickness=1.2))
        story.append(Spacer(1, 8))

        meta_table = Table(
            [
                ["Inspection ID", inspection.get("inspection_id", "-"),
                 "Date / Time", inspection.get("timestamp", "-")],
            ],
            colWidths=[80, 150, 80, 150],
        )
        meta_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # Compliance score + status
        story.append(Paragraph("Compliance Assessment", styles["SectionHeading"]))
        score_display = f"{assessment.get('score')} / 100" if assessment.get("score") is not None else "N/A"
        score_table = Table(
            [[score_display, status, f"AI Confidence: {_fmt_pct(assessment.get('confidence'))}"]],
            colWidths=[130, 150, 180],
        )
        score_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (0, 0), 20),
            ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
            ("FONTSIZE", (1, 0), (1, 0), 12),
            ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
            ("TEXTCOLOR", (1, 0), (1, 0), _status_color(status)),
            ("FONTSIZE", (2, 0), (2, 0), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 10))

        # Product information
        story.append(Paragraph("Product Information", styles["SectionHeading"]))
        product_rows = [
            ["Product name", _fmt(product.get("name"))],
            ["Brand", _fmt(product.get("brand"))],
            ["Manufacturer", _fmt(product.get("manufacturer"))],
            ["Manufacturer address", _fmt(product.get("manufacturer_address"))],
            ["Packer", _fmt(product.get("packer"))],
            ["Importer", _fmt(product.get("importer"))],
            ["Net quantity", _fmt(product.get("net_quantity"))],
            ["MRP", _fmt(product.get("mrp"))],
            ["Manufacture date", _fmt(product.get("manufacture_date"))],
            ["Pack date", _fmt(product.get("pack_date"))],
            ["Consumer care", _fmt(product.get("consumer_care"))],
            ["Country of origin", _fmt(product.get("country_of_origin"))],
        ]
        product_table = Table(product_rows, colWidths=[140, 320])
        product_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(product_table)
        story.append(Spacer(1, 10))

        # Requirements checked
        story.append(Paragraph("Requirements Checked", styles["SectionHeading"]))
        requirements = inspection.get("requirements", [])
        if requirements:
            req_rows = [["Requirement", "Detected Value", "Status", "Confidence"]]
            for r in requirements:
                req_rows.append([
                    _fmt(r.get("name")),
                    _fmt(r.get("detected_value")),
                    r.get("status", "-"),
                    _fmt_pct(r.get("confidence")),
                ])
            req_table = Table(req_rows, colWidths=[150, 150, 80, 80])
            req_table.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B3A6B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(req_table)
        else:
            story.append(Paragraph("No requirement-level data was provided by Module 2.", styles["Body"]))
        story.append(Spacer(1, 10))

        # Findings
        story.append(Paragraph("Findings", styles["SectionHeading"]))
        findings = inspection.get("findings", [])
        if findings:
            for f in findings:
                story.append(Paragraph(
                    f"<b>{f.get('severity', 'MEDIUM')} \u2014 {_fmt(f.get('type'))}</b> "
                    f"(Confidence: {_fmt_pct(f.get('confidence'))})",
                    ParagraphStyle("FindingTitle", parent=styles["Body"], textColor=_status_color(
                        "HIGH PRIORITY" if f.get("severity") in ("HIGH", "CRITICAL") else "REVIEW"
                    ), fontName="Helvetica-Bold"),
                ))
                story.append(Paragraph(f"Detected field: {_fmt(f.get('field'))}", styles["Body"]))
                story.append(Paragraph(f"Explanation: {_fmt(f.get('explanation'))}", styles["Body"]))
                story.append(Paragraph(f"Recommended action: {_fmt(f.get('recommended_action'))}", styles["Body"]))
                story.append(Spacer(1, 6))
        else:
            story.append(Paragraph("No findings were raised for this inspection.", styles["Body"]))
        story.append(Spacer(1, 6))

        # Evidence
        story.append(Paragraph("Evidence", styles["SectionHeading"]))
        evidence = inspection.get("evidence", [])
        if evidence:
            for e in evidence:
                desc = e.get("description") or e.get("image_url") or e.get("image_path") or "Evidence attached."
                story.append(Paragraph(f"\u2022 {desc}", styles["Body"]))
        else:
            story.append(Paragraph("No visual evidence attached.", styles["Body"]))
        story.append(Spacer(1, 12))

        # Disclaimer
        story.append(HRFlowable(width="100%", color=colors.HexColor("#CCCCCC"), thickness=0.6))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>{config.DISCLAIMER_TITLE}</b>", styles["Disclaimer"]))
        story.append(Paragraph(config.DISCLAIMER_TEXT, styles["Disclaimer"]))

        doc.build(story)
        return filepath

    except Exception as exc:  # noqa: BLE001 - convert everything to a clean error
        raise PDFGenerationError(f"Could not generate PDF report: {exc}")
