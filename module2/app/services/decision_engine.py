"""
Orchestrator: ties together field validation, format validation,
consistency checks, confidence handling and scoring into ONE final,
explainable ComplianceResult — the JSON object Module 3 consumes.
"""

from app.models.schemas import ProductData, ComplianceResult, Finding
from app.rules.rule_engine import rule_engine
from app.validators.field_validator import validate_required_fields
from app.validators.format_validator import validate_formats
from app.validators.consistency_validator import validate_consistency
from app.validators.confidence_validator import validate_confidence
from app.scoring.compliance_score import compute_score


def run_compliance_check(product: ProductData) -> ComplianceResult:
    rules = rule_engine.get_rules(product.product_category)

    required_findings = validate_required_fields(product, rules)
    format_findings = validate_formats(product, rules)
    consistency_findings = validate_consistency(product)
    confidence_findings = validate_confidence(product, rules)

    all_findings = required_findings + format_findings + consistency_findings + confidence_findings

    score, status = compute_score(all_findings)

    summary = {
        "passed": sum(1 for f in all_findings if f.status == "PASS"),
        "failed": sum(1 for f in all_findings if f.status == "FAIL"),
        "warnings": sum(1 for f in all_findings if f.status == "WARNING"),
        "review": sum(1 for f in all_findings if f.status == "REVIEW"),
    }

    review_required = status != "LIKELY_COMPLIANT" or summary["failed"] > 0

    return ComplianceResult(
        compliance_score=score,
        status=status,
        summary=summary,
        findings=all_findings,
        consistency_checks=consistency_findings,
        review_required=review_required,
    )
