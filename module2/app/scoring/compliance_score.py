"""
STEP: Compliance scoring.

A simple, EXPLAINABLE deduction-based score. These weights are a prototype
methodology, not an official government scoring standard — say so out loud
in your demo.
"""

from typing import List, Tuple
from app.models.schemas import Finding

SEVERITY_DEDUCTIONS = {
    "HIGH": 35,     # e.g. a missing mandatory declaration (MRP, quantity, mfg date, manufacturer)
    "MEDIUM": 15,   # e.g. low-confidence extraction, cross-panel inconsistency
    "LOW": 5,       # e.g. minor formatting issue, borderline confidence
    "INFO": 0,
}

LOW_CONFIDENCE_THRESHOLD = 0.60
REVIEW_CONFIDENCE_THRESHOLD = 0.85


def confidence_band(confidence: float) -> str:
    if confidence >= REVIEW_CONFIDENCE_THRESHOLD:
        return "CONFIDENT"
    if confidence >= LOW_CONFIDENCE_THRESHOLD:
        return "REVIEW"
    return "LOW_CONFIDENCE"


def compute_score(all_findings: List[Finding]) -> Tuple[int, str]:
    score = 100

    for finding in all_findings:
        if finding.status in ("FAIL", "WARNING", "REVIEW"):
            score -= SEVERITY_DEDUCTIONS.get(finding.severity, 5)

    score = max(0, min(100, score))

    if score >= 90:
        status = "LIKELY_COMPLIANT"
    elif score >= 70:
        status = "REVIEW_REQUIRED"
    else:
        status = "HIGH_PRIORITY_REVIEW"

    return score, status
