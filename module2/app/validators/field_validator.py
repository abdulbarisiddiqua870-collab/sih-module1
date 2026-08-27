"""
STEP: Required-field validation.
Answers only one question per rule: "Is this required field present at all?"
"""

from typing import List, Dict, Any
from app.models.schemas import ProductData, Finding


def validate_required_fields(product: ProductData, rules: List[Dict[str, Any]]) -> List[Finding]:
    findings: List[Finding] = []
    data = product.dict()

    for rule in rules:
        if not rule.get("required"):
            continue

        field_name = rule["field"]
        field_data = data.get(field_name) or {}
        value = field_data.get("value")
        confidence = field_data.get("confidence", 0.0)

        if value is None or str(value).strip() == "":
            findings.append(Finding(
                rule_id=rule["id"],
                field=field_name,
                status="FAIL",
                severity=rule.get("severity", "MEDIUM"),
                message=f"{rule['description']} — not detected on the label.",
                confidence=confidence,
                recommendation="Human verification required; declaration may be missing or unreadable.",
            ))
        else:
            findings.append(Finding(
                rule_id=rule["id"],
                field=field_name,
                status="PASS",
                severity="INFO",
                message=f"{rule['description']} — present.",
                confidence=confidence,
                recommendation="No action needed.",
            ))

    return findings
