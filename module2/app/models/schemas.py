"""
Input/Output data models for Module 2.

Module 1 sends us a ProductData object: every declared field, plus an
OCR confidence score for that field. We never touch images ourselves.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FieldValue(BaseModel):
    """A single extracted field + how confident Module 1's OCR was about it."""
    value: Optional[str] = None
    confidence: float = 0.0


class ProductData(BaseModel):
    """
    Structured extraction handed off by Module 1.
    Keep this schema STABLE — Module 1 depends on it staying fixed.
    """
    product_name: FieldValue
    mrp: FieldValue
    net_quantity: FieldValue
    manufacturer: FieldValue
    manufacturing_date: FieldValue
    consumer_care: FieldValue

    # Optional: if Module 1 detected the same field twice (e.g. front vs
    # back panel), it can send both readings here for consistency checks.
    duplicate_readings: Optional[Dict[str, List[str]]] = None

    # Optional: font size in points, if Module 1's vision stage measured it
    font_sizes: Optional[Dict[str, float]] = None

    product_category: str = "packaged_food"  # which rule-set to apply


class Finding(BaseModel):
    rule_id: str
    field: str
    status: str          # "PASS" | "FAIL" | "WARNING" | "REVIEW"
    severity: str         # "HIGH" | "MEDIUM" | "LOW" | "INFO"
    message: str
    confidence: float
    recommendation: str


class ComplianceResult(BaseModel):
    compliance_score: int
    status: str  # LIKELY_COMPLIANT | REVIEW_REQUIRED | HIGH_PRIORITY_REVIEW
    summary: Dict[str, int]
    findings: List[Finding]
    consistency_checks: List[Finding] = Field(default_factory=list)
    review_required: bool
    disclaimer: str = (
        "AI-assisted preliminary screening only. Not a legal determination "
        "of compliance under the Legal Metrology (Packaged Commodities) "
        "Rules, 2011. Final decisions require human verification against "
        "current official notifications."
    )
