"""
Module 2 client / adapter.

Module 3 talks only to Module 2 through this file. The live adapter accepts
Module 1's ProductData-shaped JSON, sends it to Module 2 /analyze, and maps
Module 2's decision into Module 3's normalized inspection shape.
"""

import json
import uuid
from datetime import datetime, timezone

import requests

import config
from mock.mock_data import get_random_mock_inspection
from services.normalizer import normalize_inspection, NormalizationError


class Module2Error(Exception):
    """Raised for any problem obtaining or parsing a Module 2 response."""


def _call_live_module2(payload: dict) -> dict:
    """Call the bundled/external Module 2 /analyze endpoint and adapt its result."""
    try:
        response = requests.post(
            config.MODULE2_INSPECT_ENDPOINT,
            json=_to_module2_payload(payload or {}),
            timeout=config.MODULE2_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        raise Module2Error(
            f"Module 2 did not respond within {config.MODULE2_TIMEOUT_SECONDS} seconds."
        )
    except requests.exceptions.ConnectionError:
        raise Module2Error(
            f"Could not connect to Module 2 at {config.MODULE2_API_URL}. "
            "Confirm the Module 2 service is running and MODULE2_API_URL is correct."
        )
    except requests.exceptions.RequestException as exc:
        raise Module2Error(f"Module 2 request failed: {exc}")

    if response.status_code != 200:
        raise Module2Error(
            f"Module 2 returned HTTP {response.status_code}. "
            f"Response: {response.text[:500]}"
        )

    try:
        raw_result = response.json()
    except ValueError:
        raise Module2Error("Module 2 returned a response that was not valid JSON.")

    return _adapt_module2_result(raw_result, payload or {})


def _field(value):
    """Convert a plain Module 1 value or {value, confidence} object to FieldValue-like data."""
    if isinstance(value, dict):
        return {
            "value": value.get("value"),
            "confidence": value.get("confidence", 0.0),
        }
    return {"value": value, "confidence": 1.0 if value not in (None, "") else 0.0}


def _to_module2_payload(payload: dict) -> dict:
    """Normalize common Module 1 payload shapes into Module 2 ProductData."""
    if not isinstance(payload, dict):
        raise Module2Error("Module 1 payload must be a JSON object.")

    # Already in Module 2 ProductData shape.
    required = ("product_name", "mrp", "net_quantity", "manufacturer", "manufacturing_date", "consumer_care")
    if all(k in payload for k in required):
        return payload

    # Also accept Module 3's flatter product object for integration testing.
    product = payload.get("product") if isinstance(payload.get("product"), dict) else payload
    return {
        "product_name": _field(product.get("product_name", product.get("name"))),
        "mrp": _field(product.get("mrp")),
        "net_quantity": _field(product.get("net_quantity")),
        "manufacturer": _field(product.get("manufacturer")),
        "manufacturing_date": _field(product.get("manufacturing_date", product.get("manufacture_date"))),
        "consumer_care": _field(product.get("consumer_care")),
        "duplicate_readings": product.get("duplicate_readings"),
        "font_sizes": product.get("font_sizes"),
        "product_category": product.get("product_category", "packaged_food"),
    }


def _avg_confidence(product_data: dict) -> float:
    fields = ["product_name", "mrp", "net_quantity", "manufacturer", "manufacturing_date", "consumer_care"]
    values = [_field(product_data.get(k)).get("confidence", 0.0) for k in fields]
    return round(sum(values) / len(values), 4) if values else 0.0


def _status_for_field(field: str, findings: list) -> str:
    field_findings = [f for f in findings if f.get("field") == field]
    if any(f.get("status") == "FAIL" for f in field_findings):
        return "HIGH PRIORITY"
    if any(f.get("status") in ("WARNING", "REVIEW") for f in field_findings):
        return "REVIEW"
    return "PASS"


def _adapt_module2_result(result: dict, input_payload: dict) -> dict:
    """Convert Module 2 ComplianceResult into the shape Module 3 already understands."""
    product_data = _to_module2_payload(input_payload)
    source_product = {
        "name": _field(product_data.get("product_name")).get("value"),
        "brand": None,
        "manufacturer": _field(product_data.get("manufacturer")).get("value"),
        "manufacturer_address": None,
        "packer": None,
        "importer": None,
        "net_quantity": _field(product_data.get("net_quantity")).get("value"),
        "mrp": _field(product_data.get("mrp")).get("value"),
        "manufacture_date": _field(product_data.get("manufacturing_date")).get("value"),
        "pack_date": None,
        "consumer_care": _field(product_data.get("consumer_care")).get("value"),
        "country_of_origin": None,
    }

    findings = result.get("findings", [])
    requirements = []
    field_labels = {
        "product_name": "Product name",
        "mrp": "MRP",
        "net_quantity": "Net quantity",
        "manufacturer": "Manufacturer details",
        "manufacturing_date": "Manufacture date",
        "consumer_care": "Consumer care information",
    }
    for field, label in field_labels.items():
        field_data = _field(product_data.get(field))
        requirements.append({
            "name": label,
            "status": _status_for_field(field, findings),
            "confidence": field_data.get("confidence", 0.0),
            "detected_value": field_data.get("value"),
        })

    normalized_findings = []
    for finding in findings:
        normalized_findings.append({
            "type": finding.get("rule_id") or finding.get("field") or "COMPLIANCE_FINDING",
            "field": finding.get("field"),
            "severity": finding.get("severity", "MEDIUM"),
            "status": finding.get("status", "REVIEW"),
            "confidence": finding.get("confidence"),
            "explanation": finding.get("message", "No explanation provided by Module 2."),
            "recommended_action": finding.get("recommendation", "Verify the original package manually."),
        })

    raw_status = result.get("status")
    status_map = {
        "LIKELY_COMPLIANT": "PASS",
        "REVIEW_REQUIRED": "REVIEW",
        "HIGH_PRIORITY_REVIEW": "HIGH PRIORITY",
    }

    return {
        "inspection_id": f"INS-{uuid.uuid4().hex[:8].upper()}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "product": source_product,
        "assessment": {
            "score": result.get("compliance_score"),
            "status": status_map.get(raw_status, raw_status),
            "confidence": _avg_confidence(product_data),
        },
        "requirements": requirements,
        "findings": normalized_findings,
        "evidence": [],
        "source_image": None,
        "warnings": ["Live result adapted from SIH26034 Module 2 ComplianceResult."],
    }


def get_inspection(mode: str, payload: dict = None, raw_json_text: str = None) -> dict:
    """
    Obtain one inspection, already normalized, regardless of source.

    mode:
      mock  - generated simulated Module 2 response
      paste - raw Module 2 response
      live  - ProductData from Module 1 -> Module 2 /analyze
    """
    if mode == "mock" or (mode == "live" and config.MOCK_MODE):
        raw = get_random_mock_inspection()

    elif mode == "paste":
        if not raw_json_text or not raw_json_text.strip():
            raise Module2Error("No JSON was provided to load.")
        try:
            raw = json.loads(raw_json_text)
        except json.JSONDecodeError as exc:
            raise Module2Error(f"That text is not valid JSON ({exc.msg} at line {exc.lineno}).")

    elif mode == "live":
        raw = _call_live_module2(payload or {})

    else:
        raise Module2Error(f"Unknown inspection source mode: {mode}")

    try:
        return normalize_inspection(raw)
    except NormalizationError as exc:
        raise Module2Error(str(exc))
