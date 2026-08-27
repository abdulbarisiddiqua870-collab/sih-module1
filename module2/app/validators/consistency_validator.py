"""
STEP: Cross-field consistency checking.
If Module 1 detected the same declaration in more than one place on the
package (e.g. net quantity printed on both front and back panel) and the
readings disagree, that's a red flag worth surfacing on its own.
"""

from typing import List
from app.models.schemas import ProductData, Finding


def validate_consistency(product: ProductData) -> List[Finding]:
    findings: List[Finding] = []

    if not product.duplicate_readings:
        return findings

    for field_name, readings in product.duplicate_readings.items():
        cleaned = [str(r).strip().lower() for r in readings if r and str(r).strip()]
        unique_values = set(cleaned)

        if len(unique_values) > 1:
            findings.append(Finding(
                rule_id="CONSISTENCY-" + field_name.upper(),
                field=field_name,
                status="WARNING",
                severity="MEDIUM",
                message=(
                    f"Conflicting values detected for '{field_name}' across the "
                    f"package: {', '.join(sorted(unique_values))}."
                ),
                confidence=0.0,
                recommendation="Human verification required to resolve which panel is correct.",
            ))

    return findings
