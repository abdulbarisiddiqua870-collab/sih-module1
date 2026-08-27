"""
Normalization / adapter layer.

Module 3 must never assume Module 2's JSON shape is exactly the
example in the spec. This module is the ONLY place that reads raw
Module 2 output. Everything downstream (UI, database, PDF, analytics)
only ever sees the normalized shape produced by `normalize_inspection`.

Normalized shape:

{
  "inspection_id": str,
  "timestamp": str (ISO 8601),
  "product": {
      "name", "brand", "manufacturer", "manufacturer_address",
      "packer", "importer", "net_quantity", "mrp",
      "manufacture_date", "pack_date", "consumer_care",
      "country_of_origin"
  },
  "assessment": {"score": int|None, "status": str, "confidence": float|None},
  "requirements": [{"name","status","confidence","detected_value"}],
  "findings": [{"type","field","severity","status","confidence",
                "explanation","recommended_action"}],
  "evidence": [{"description","image_url","image_path","bbox"}],
  "source_image": str|None,
  "finding_count": int,
  "warnings": [str, ...]   # normalization notes, not compliance findings
}
"""

import uuid
from datetime import datetime, timezone

from config import STATUS_PASS, STATUS_REVIEW, STATUS_HIGH_PRIORITY

PRODUCT_FIELDS = [
    "name", "brand", "manufacturer", "manufacturer_address", "packer",
    "importer", "net_quantity", "mrp", "manufacture_date", "pack_date",
    "consumer_care", "country_of_origin",
]


class NormalizationError(Exception):
    """Raised when raw data is so malformed it cannot be normalized at all."""


def _first(d, keys, default=None):
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _normalize_status(raw_status, warnings):
    if raw_status is None:
        warnings.append("Status missing from Module 2 output; defaulted to REVIEW.")
        return STATUS_REVIEW

    s = str(raw_status).strip().upper().replace("_", " ")
    if s in (STATUS_PASS, "PASSED", "OK", "COMPLIANT"):
        return STATUS_PASS
    if s in (STATUS_HIGH_PRIORITY, "HIGH", "CRITICAL", "NON COMPLIANT", "FAIL", "FAILED"):
        return STATUS_HIGH_PRIORITY
    if s in (STATUS_REVIEW, "WARNING", "NEEDS REVIEW"):
        return STATUS_REVIEW

    warnings.append(f"Unrecognized status '{raw_status}' from Module 2; defaulted to REVIEW.")
    return STATUS_REVIEW


def _normalize_score(raw_score, warnings):
    if raw_score is None:
        warnings.append("Compliance score missing from Module 2 output.")
        return None
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        warnings.append(f"Compliance score '{raw_score}' was not numeric.")
        return None
    if score <= 1.0:
        score *= 100
    return max(0, min(100, round(score)))


def _normalize_confidence(raw_conf, warnings=None):
    if raw_conf is None:
        return None
    try:
        conf = float(raw_conf)
    except (TypeError, ValueError):
        return None
    if conf > 1.0:
        conf = conf / 100.0
    return max(0.0, min(1.0, conf))


def _normalize_product(raw_product, warnings):
    raw_product = raw_product if isinstance(raw_product, dict) else {}
    product = {}
    for field in PRODUCT_FIELDS:
        product[field] = raw_product.get(field)
    if not product.get("name"):
        warnings.append("Product name missing from Module 2 output.")
        product["name"] = "Unknown product"
    return product


def _normalize_requirements(raw_requirements, warnings):
    if not isinstance(raw_requirements, list):
        if raw_requirements:
            warnings.append("Requirements field was not a list; ignored.")
        return []

    normalized = []
    for i, item in enumerate(raw_requirements):
        if not isinstance(item, dict):
            continue
        normalized.append({
            "name": _first(item, ["name", "requirement", "field"], f"Requirement {i + 1}"),
            "status": _normalize_status(_first(item, ["status", "result"]), warnings),
            "confidence": _normalize_confidence(_first(item, ["confidence", "score"])),
            "detected_value": _first(item, ["detected_value", "value", "detected"]),
        })
    return normalized


def _normalize_findings(raw_findings, warnings):
    if not isinstance(raw_findings, list):
        if raw_findings:
            warnings.append("Findings field was not a list; ignored.")
        return []

    normalized = []
    for i, item in enumerate(raw_findings):
        if not isinstance(item, dict):
            continue
        severity = str(_first(item, ["severity", "priority"], "MEDIUM")).strip().upper()
        if severity not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            severity = "MEDIUM"
        normalized.append({
            "type": _first(item, ["type", "category"], "FINDING"),
            "field": _first(item, ["field", "attribute"]),
            "severity": severity,
            "status": _normalize_status(_first(item, ["status", "result"]), []),
            "confidence": _normalize_confidence(_first(item, ["confidence"])),
            "explanation": _first(item, ["explanation", "description", "message"],
                                   "No explanation provided by Module 2."),
            "recommended_action": _first(item, ["recommended_action", "action", "recommendation"],
                                          "Verify the package manually."),
        })
    return normalized


def _normalize_evidence(raw_evidence, source_image, warnings):
    normalized = []
    if isinstance(raw_evidence, list):
        for item in raw_evidence:
            if isinstance(item, dict):
                normalized.append({
                    "description": _first(item, ["description", "note"]),
                    "image_url": _first(item, ["image_url", "url"]),
                    "image_path": _first(item, ["image_path", "path"]),
                    "bbox": item.get("bbox") or item.get("bounding_box"),
                })
            elif isinstance(item, str):
                normalized.append({"description": item, "image_url": None, "image_path": None, "bbox": None})
    elif raw_evidence:
        warnings.append("Evidence field was not a list; ignored.")

    if source_image and not normalized:
        normalized.append({"description": None, "image_url": source_image, "image_path": None, "bbox": None})

    return normalized


def normalize_inspection(raw):
    """
    Convert a raw Module 2 response (a dict, possibly with a different
    shape than the reference example) into Module 3's normalized
    inspection model.
    """
    if not isinstance(raw, dict):
        raise NormalizationError("Module 2 response was not a JSON object.")

    warnings = []

    inspection_id = _first(raw, ["inspection_id", "id"]) or f"INS-{uuid.uuid4().hex[:8].upper()}"
    timestamp = _first(raw, ["timestamp", "created_at", "time"]) or datetime.now(timezone.utc).isoformat()

    assessment_block = raw.get("assessment") if isinstance(raw.get("assessment"), dict) else {}
    score_raw = _first(assessment_block, ["score"]) or _first(raw, ["compliance_score", "score"])
    status_raw = _first(assessment_block, ["status"]) or _first(raw, ["decision", "status"])
    confidence_raw = _first(assessment_block, ["confidence"]) or _first(raw, ["confidence"])

    assessment = {
        "score": _normalize_score(score_raw, warnings),
        "status": _normalize_status(status_raw, warnings),
        "confidence": _normalize_confidence(confidence_raw),
    }

    requirements = _normalize_requirements(raw.get("requirements"), warnings)
    findings = _normalize_findings(raw.get("findings"), warnings)
    evidence = _normalize_evidence(raw.get("evidence"), raw.get("source_image"), warnings)
    product = _normalize_product(raw.get("product"), warnings)

    return {
        "inspection_id": str(inspection_id),
        "timestamp": str(timestamp),
        "product": product,
        "assessment": assessment,
        "requirements": requirements,
        "findings": findings,
        "evidence": evidence,
        "source_image": raw.get("source_image"),
        "finding_count": len(findings),
        "warnings": warnings,
    }
