"""
STEP: Format validation.
Checks whether a PRESENT field actually looks like the right kind of data
(a real price, a real quantity+unit, a real MM/YYYY date) rather than
garbage OCR text.
"""

import re
from typing import List, Dict, Any
from app.models.schemas import ProductData, Finding


def validate_formats(product: ProductData, rules: List[Dict[str, Any]]) -> List[Finding]:
    findings: List[Finding] = []
    data = product.dict()

    for rule in rules:
        pattern = rule.get("format_regex")
        if not pattern:
            continue  # this rule has no format check, only a presence check

        field_name = rule["field"]
        field_data = data.get(field_name) or {}
        value = field_data.get("value")
        confidence = field_data.get("confidence", 0.0)

        if value is None or str(value).strip() == "":
            continue  # already reported as missing by field_validator

        if re.match(pattern, str(value).strip(), flags=re.IGNORECASE):
            findings.append(Finding(
                rule_id=f"{rule['id']}-FORMAT",
                field=field_name,
                status="PASS",
                severity="INFO",
                message=f"{field_name} format looks valid ('{value}').",
                confidence=confidence,
                recommendation="No action needed.",
            ))
        else:
            findings.append(Finding(
                rule_id=f"{rule['id']}-FORMAT",
                field=field_name,
                status="WARNING",
                severity="LOW" if confidence < 0.7 else "MEDIUM",
                message=(
                    f"{field_name} value ('{value}') does not match the expected "
                    f"format for this declaration."
                ),
                confidence=confidence,
                recommendation="Check original label; OCR misread or non-standard format.",
            ))

    return findings
