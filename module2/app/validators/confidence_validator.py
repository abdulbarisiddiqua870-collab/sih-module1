"""
STEP: Confidence-aware handling.

This is what stops the system from confidently declaring a package
non-compliant just because OCR misread something. A field can be PRESENT
and FORMAT-VALID and still deserve a human look if Module 1 wasn't sure
about it.

Bands (matches compliance_score.confidence_band):
    >= 0.85            -> CONFIDENT   (no finding raised)
    0.60 - 0.85        -> REVIEW      (LOW severity finding)
    <  0.60            -> LOW_CONF    (MEDIUM severity finding)
"""

from typing import List, Dict, Any
from app.models.schemas import ProductData, Finding
from app.scoring.compliance_score import confidence_band, REVIEW_CONFIDENCE_THRESHOLD


def validate_confidence(product: ProductData, rules: List[Dict[str, Any]]) -> List[Finding]:
    findings: List[Finding] = []
    data = product.dict()
    required_fields = {rule["field"] for rule in rules if rule.get("required")}

    for field_name in required_fields:
        field_data = data.get(field_name) or {}
        value = field_data.get("value")
        confidence = field_data.get("confidence", 0.0)

        if value is None or str(value).strip() == "":
            continue  # already handled by field_validator; nothing to be "unsure" about

        band = confidence_band(confidence)
        if band == "CONFIDENT":
            continue

        severity = "MEDIUM" if band == "LOW_CONFIDENCE" else "LOW"
        findings.append(Finding(
            rule_id=f"CONF-{field_name.upper()}",
            field=field_name,
            status="REVIEW",
            severity=severity,
            message=(
                f"'{field_name}' was extracted with {band.replace('_', ' ').lower()} "
                f"OCR confidence ({confidence:.0%}); value may be misread."
            ),
            confidence=confidence,
            recommendation="Flag for human review rather than an automatic violation.",
        ))

    return findings
