"""
Realistic MOCK Module 2 output.

This is what Module 3 pretends Module 2 sent it when MOCK_MODE=true.
The shapes here are intentionally slightly inconsistent with each
other (different key spellings, missing optional fields) so that the
normalizer in services/normalizer.py is exercised the same way it
will be by a real, imperfect Module 2 integration.
"""

import copy
import random
import uuid
from datetime import datetime, timedelta, timezone

_BASE_SAMPLES = [
    {
        "inspection_id": "INS-2026-0001",
        "timestamp": "2026-08-20T09:12:00",
        "product": {
            "name": "Sunrise Refined Sunflower Oil",
            "brand": "Sunrise",
            "manufacturer": "ABC Foods Pvt Ltd",
            "manufacturer_address": "Plot 14, Industrial Area, Bengaluru, Karnataka",
            "packer": "ABC Foods Pvt Ltd",
            "importer": None,
            "net_quantity": "1 L",
            "mrp": "\u20b9195",
            "manufacture_date": "07/2026",
            "pack_date": None,
            "consumer_care": None,
            "country_of_origin": "India",
        },
        "assessment": {"score": 82, "status": "REVIEW", "confidence": 0.91},
        "requirements": [
            {"name": "Manufacturer details", "status": "PASS", "confidence": 0.96, "detected_value": "ABC Foods Pvt Ltd"},
            {"name": "Net quantity", "status": "PASS", "confidence": 0.94, "detected_value": "1 L"},
            {"name": "MRP", "status": "PASS", "confidence": 0.93, "detected_value": "\u20b9195"},
            {"name": "Consumer care information", "status": "FAIL", "confidence": 0.94, "detected_value": None},
            {"name": "Country of origin", "status": "PASS", "confidence": 0.9, "detected_value": "India"},
        ],
        "findings": [
            {
                "type": "MISSING_DECLARATION",
                "field": "consumer_care",
                "severity": "HIGH",
                "status": "FAIL",
                "confidence": 0.94,
                "explanation": "Consumer-care information was not detected on the package.",
                "recommended_action": "Verify the package manually for a consumer-care declaration.",
            }
        ],
        "evidence": [],
        "source_image": None,
    },
    {
        "inspection_id": "INS-2026-0002",
        "timestamp": "2026-08-21T14:44:00",
        "product": {
            "name": "GreenLeaf Basmati Rice",
            "brand": "GreenLeaf",
            "manufacturer": "GreenLeaf Agro Exports",
            "manufacturer_address": "Karnal, Haryana",
            "packer": "GreenLeaf Agro Exports",
            "importer": None,
            "net_quantity": "5 kg",
            "mrp": "\u20b9540",
            "manufacture_date": "06/2026",
            "pack_date": "06/2026",
            "consumer_care": "1800-102-3344",
            "country_of_origin": "India",
        },
        "assessment": {"score": 97, "status": "PASS", "confidence": 0.98},
        "requirements": [
            {"name": "Manufacturer details", "status": "PASS", "confidence": 0.98, "detected_value": "GreenLeaf Agro Exports"},
            {"name": "Net quantity", "status": "PASS", "confidence": 0.97, "detected_value": "5 kg"},
            {"name": "MRP", "status": "PASS", "confidence": 0.97, "detected_value": "\u20b9540"},
            {"name": "Consumer care information", "status": "PASS", "confidence": 0.95, "detected_value": "1800-102-3344"},
            {"name": "Country of origin", "status": "PASS", "confidence": 0.96, "detected_value": "India"},
        ],
        "findings": [],
        "evidence": [],
        "source_image": None,
    },
    {
        "inspection_id": "INS-2026-0003",
        "timestamp": "2026-08-22T11:05:00",
        "product": {
            "name": "Nova Instant Noodles",
            "brand": "Nova",
            "manufacturer": None,
            "manufacturer_address": None,
            "packer": "Nova Snacks Pvt Ltd",
            "importer": None,
            "net_quantity": None,
            "mrp": "\u20b935",
            "manufacture_date": None,
            "pack_date": None,
            "consumer_care": None,
            "country_of_origin": None,
        },
        # Note the alternate key name "compliance_score" / "decision" on purpose,
        # to exercise the normalizer's defensive field lookup.
        "compliance_score": 41,
        "decision": "HIGH_PRIORITY",
        "confidence": 0.88,
        "requirements": [
            {"name": "Manufacturer details", "status": "FAIL", "confidence": 0.9, "detected_value": None},
            {"name": "Net quantity", "status": "FAIL", "confidence": 0.87, "detected_value": None},
            {"name": "MRP", "status": "PASS", "confidence": 0.92, "detected_value": "\u20b935"},
            {"name": "Consumer care information", "status": "FAIL", "confidence": 0.9, "detected_value": None},
            {"name": "Country of origin", "status": "FAIL", "confidence": 0.85, "detected_value": None},
        ],
        "findings": [
            {
                "type": "MISSING_DECLARATION",
                "field": "manufacturer",
                "severity": "CRITICAL",
                "status": "FAIL",
                "confidence": 0.9,
                "explanation": "No manufacturer or packer identity details could be located.",
                "recommended_action": "Reject listing until manufacturer details are declared.",
            },
            {
                "type": "MISSING_DECLARATION",
                "field": "net_quantity",
                "severity": "HIGH",
                "status": "FAIL",
                "confidence": 0.87,
                "explanation": "Net quantity declaration was not detected.",
                "recommended_action": "Verify package manually for net quantity declaration.",
            },
            {
                "type": "MISSING_DECLARATION",
                "field": "consumer_care",
                "severity": "MEDIUM",
                "status": "FAIL",
                "confidence": 0.9,
                "explanation": "Consumer-care information was not detected.",
                "recommended_action": "Verify the package manually.",
            },
        ],
        "evidence": [
            {"description": "Front-of-pack image shows no declaration block on the reverse panel."}
        ],
        "source_image": None,
    },
    {
        "inspection_id": "INS-2026-0004",
        "timestamp": "2026-08-23T16:30:00",
        "product": {
            "name": "Meadow Farms Toned Milk",
            "brand": "Meadow Farms",
            "manufacturer": "Meadow Farms Dairy Ltd",
            "manufacturer_address": "Mysuru, Karnataka",
            "packer": "Meadow Farms Dairy Ltd",
            "importer": None,
            "net_quantity": "500 ml",
            "mrp": "\u20b930",
            "manufacture_date": "08/2026",
            "pack_date": "08/2026",
            "consumer_care": "care@meadowfarms.in",
            "country_of_origin": "India",
        },
        "assessment": {"score": 88, "status": "REVIEW", "confidence": 0.93},
        "requirements": [
            {"name": "Manufacturer details", "status": "PASS", "confidence": 0.95, "detected_value": "Meadow Farms Dairy Ltd"},
            {"name": "Net quantity", "status": "PASS", "confidence": 0.95, "detected_value": "500 ml"},
            {"name": "MRP", "status": "PASS", "confidence": 0.94, "detected_value": "\u20b930"},
            {"name": "Consumer care information", "status": "PASS", "confidence": 0.9, "detected_value": "care@meadowfarms.in"},
            {"name": "Manufacture / pack date", "status": "REVIEW", "confidence": 0.7, "detected_value": "08/2026"},
        ],
        "findings": [
            {
                "type": "LOW_CONFIDENCE_FIELD",
                "field": "pack_date",
                "severity": "MEDIUM",
                "status": "REVIEW",
                "confidence": 0.7,
                "explanation": "Pack date was detected with lower-than-usual confidence and may be misread.",
                "recommended_action": "Manually confirm the printed pack date.",
            }
        ],
        "evidence": [
            {"description": "Date stamp region was partially smudged in the captured image."}
        ],
        "source_image": None,
    },
    {
        "inspection_id": "INS-2026-0005",
        "timestamp": "2026-08-24T10:02:00",
        "product": {
            "name": "Zesty Tomato Ketchup",
            "brand": "Zesty",
            "manufacturer": "Zesty Foods Pvt Ltd",
            "manufacturer_address": "Pune, Maharashtra",
            "packer": "Zesty Foods Pvt Ltd",
            "importer": None,
            "net_quantity": "200 g",
            "mrp": None,
            "manufacture_date": "05/2026",
            "pack_date": None,
            "consumer_care": "1800-555-2020",
            "country_of_origin": "India",
        },
        "assessment": {"score": 68, "status": "REVIEW", "confidence": 0.89},
        "requirements": [
            {"name": "Manufacturer details", "status": "PASS", "confidence": 0.95, "detected_value": "Zesty Foods Pvt Ltd"},
            {"name": "Net quantity", "status": "PASS", "confidence": 0.93, "detected_value": "200 g"},
            {"name": "MRP", "status": "FAIL", "confidence": 0.91, "detected_value": None},
            {"name": "Consumer care information", "status": "PASS", "confidence": 0.9, "detected_value": "1800-555-2020"},
        ],
        "findings": [
            {
                "type": "MISSING_DECLARATION",
                "field": "mrp",
                "severity": "HIGH",
                "status": "FAIL",
                "confidence": 0.91,
                "explanation": "Maximum Retail Price declaration was not detected on the package.",
                "recommended_action": "Verify the package manually for an MRP declaration.",
            }
        ],
        "evidence": [],
        "source_image": None,
    },
    {
        "inspection_id": "INS-2026-0006",
        "timestamp": "2026-08-25T18:20:00",
        "product": {
            "name": "Highland Wheat Flour (Atta)",
            "brand": "Highland",
            "manufacturer": "Highland Mills Pvt Ltd",
            "manufacturer_address": "Ludhiana, Punjab",
            "packer": "Highland Mills Pvt Ltd",
            "importer": None,
            "net_quantity": "10 kg",
            "mrp": "\u20b9420",
            "manufacture_date": "07/2026",
            "pack_date": "07/2026",
            "consumer_care": "1800-999-1111",
            "country_of_origin": "India",
        },
        "assessment": {"score": 95, "status": "PASS", "confidence": 0.97},
        "requirements": [
            {"name": "Manufacturer details", "status": "PASS", "confidence": 0.97, "detected_value": "Highland Mills Pvt Ltd"},
            {"name": "Net quantity", "status": "PASS", "confidence": 0.97, "detected_value": "10 kg"},
            {"name": "MRP", "status": "PASS", "confidence": 0.96, "detected_value": "\u20b9420"},
            {"name": "Consumer care information", "status": "PASS", "confidence": 0.95, "detected_value": "1800-999-1111"},
        ],
        "findings": [],
        "evidence": [],
        "source_image": None,
    },
]


def get_all_seed_samples():
    """Return deep copies of every base sample, used to seed an empty DB."""
    return [copy.deepcopy(s) for s in _BASE_SAMPLES]


def get_random_mock_inspection():
    """
    Return one fresh mock Module 2 response, as if a new inspection had
    just been run. A new inspection_id and current timestamp are stamped
    on so repeated demo runs look distinct in the dashboard/history.
    """
    sample = copy.deepcopy(random.choice(_BASE_SAMPLES))
    sample["inspection_id"] = f"INS-{uuid.uuid4().hex[:8].upper()}"
    sample["timestamp"] = datetime.now(timezone.utc).isoformat()
    return sample
