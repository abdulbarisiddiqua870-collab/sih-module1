import pytest

from module1.extraction.parser import extract_fields
from module1.extraction.validation import (
    validate_best_before,
    validate_contact,
    validate_entity_name,
    validate_mrp_amount,
    validate_product_name,
)
from module1.models.schemas import (
    BEST_BEFORE_USE_BY,
    CONSUMER_CARE,
    MANUFACTURE_PACK_IMPORT_DATE,
    MANUFACTURER_NAME,
    MRP,
    NET_QUANTITY,
    PRODUCT_NAME,
    DetectionStatus,
)
from module1.ocr.engine import OcrLine, OcrResult


def make_line(text: str, y: int, conf: float = 0.92, height: int = 24, width: int | None = None) -> OcrLine:
    if width is None:
        width = max(60, len(text) * 12)
    return OcrLine(
        text=text,
        confidence=conf,
        bounding_box=[40, y, 40 + width, y + height],
        char_height_px=height,
    )


def extract_single(text: str, y: int = 30, conf: float = 0.92):
    return extract_fields(OcrResult(raw_text=text, cleaned_text=text, lines=[make_line(text, y, conf)]), image_height_px=1000)


def test_tax_statement_not_accepted_as_product_name():
    fields, unmapped = extract_single("incl. all taxes", y=20)
    assert fields[PRODUCT_NAME].detection_status == DetectionStatus.NOT_DETECTED
    assert "incl. all taxes" in [d.text for d in unmapped]


def test_valid_title_accepted_as_product_name():
    fields, _ = extract_single("CRISPY POTATO CHIPS", y=20)
    result = fields[PRODUCT_NAME]
    assert result.value == "CRISPY POTATO CHIPS"
    assert result.detection_status == DetectionStatus.DETECTED


def test_address_like_line_rejected_as_product_name():
    fields, _ = extract_single("Plot 42, Industrial Area Phase 2, 201305", y=20)
    assert fields[PRODUCT_NAME].detection_status == DetectionStatus.NOT_DETECTED


@pytest.mark.parametrize(
    "text",
    [
        "Nutritional Information",
        "Ingredients: Wheat Flour",
        "Store in a cool dry place",
        "Cooking Instructions: Boil for 5 minutes",
        "INFORMATION",
        "SPECIALITIES,",
    ],
)
def test_product_name_rejects_non_title_packaging_text(text):
    fields, _ = extract_single(text, y=20)
    assert fields[PRODUCT_NAME].detection_status == DetectionStatus.NOT_DETECTED


@pytest.mark.parametrize("text", ["MRP \u20b950", "M.R.P. Rs 50", "MRP: Rs. 50.00"])
def test_mrp_canonical_forms_accepted(text):
    fields, _ = extract_single(text, y=400)
    result = fields[MRP]
    assert result.value is not None
    assert float(result.value.replace(",", "")) > 0
    assert result.detection_status == DetectionStatus.DETECTED


def test_phone_number_not_accepted_as_mrp():
    fields, _ = extract_single("1800-123-4567", y=400)
    assert fields[MRP].detection_status == DetectionStatus.NOT_DETECTED


def test_bare_currency_without_keyword_is_uncertain_not_detected():
    fields, _ = extract_single("\u20b9 50", y=400)
    assert fields[MRP].detection_status == DetectionStatus.UNCERTAIN
    assert fields[MRP].value == "50"


def test_standalone_gram_quantity_accepted():
    fields, _ = extract_single("500 g", y=300)
    result = fields[NET_QUANTITY]
    assert result.value == "500 g"
    assert result.detection_status == DetectionStatus.DETECTED or result.detection_status == DetectionStatus.UNCERTAIN


def test_arbitrary_number_not_accepted_as_net_quantity():
    fields, _ = extract_single("12345678", y=300)
    assert fields[NET_QUANTITY].detection_status == DetectionStatus.NOT_DETECTED


@pytest.mark.parametrize(
    "text",
    [
        "Mfg Date: 08/2026",
        "Packed on 15/08/2026",
        "Mfd: Aug 2026",
        "Imported: 2026-08",
    ],
)
def test_valid_date_shapes_accepted_for_manufacture_date(text):
    fields, _ = extract_fields(
        OcrResult(raw_text=text, cleaned_text=text, lines=[make_line(text, y=200)]),
        image_height_px=1000,
    )
    result = fields[MANUFACTURE_PACK_IMPORT_DATE]
    assert result.value is not None
    assert result.detection_status == DetectionStatus.DETECTED


def test_unrelated_numbers_not_treated_as_dates():
    fields, _ = extract_single("Batch No 4821993577", y=200)
    assert fields[MANUFACTURE_PACK_IMPORT_DATE].detection_status == DetectionStatus.NOT_DETECTED


def test_best_before_with_duration_detected():
    fields, _ = extract_single("Best Before: 4 months from packaging", y=500)
    assert fields[BEST_BEFORE_USE_BY].detection_status == DetectionStatus.DETECTED


def test_best_before_with_vague_detail_becomes_uncertain():
    fields, _ = extract_single("Best Before: see side of pack", y=500)
    result = fields[BEST_BEFORE_USE_BY]
    assert result.value is not None
    assert result.detection_status == DetectionStatus.UNCERTAIN


def test_consumer_care_email_accepted():
    fields, _ = extract_single("Customer Care: care@itc.in", y=800)
    assert fields[CONSUMER_CARE].value == "care@itc.in"
    assert fields[CONSUMER_CARE].detection_status == DetectionStatus.DETECTED


def test_consumer_care_url_accepted():
    fields, _ = extract_single("Helpline: www.snackworks.example/help", y=800)
    assert fields[CONSUMER_CARE].value is not None
    assert "www." in fields[CONSUMER_CARE].value


def test_unrelated_text_without_keyword_not_consumer_care():
    fields, _ = extract_single("Offer valid till 9876543210", y=800)
    assert fields[CONSUMER_CARE].detection_status == DetectionStatus.NOT_DETECTED


def test_stopword_rejected_as_manufacturer_name():
    fields, _ = extract_single("Mfd. ON", y=100)
    assert fields[MANUFACTURER_NAME].detection_status == DetectionStatus.NOT_DETECTED


@pytest.mark.parametrize("text", ["& Packed By", "COMMODITIES RULES 2011"])
def test_entity_noise_is_not_assigned_as_a_manufacturer(text):
    fields, _ = extract_single(text, y=100)
    assert fields[MANUFACTURER_NAME].detection_status == DetectionStatus.NOT_DETECTED


def test_weak_product_candidate_stays_uncertain_even_with_high_ocr_confidence():
    fields, _ = extract_single("Kur", y=20, conf=0.95)
    result = fields[PRODUCT_NAME]
    assert result.detection_status == DetectionStatus.UNCERTAIN
    assert result.confidence < 0.45


def test_validator_units():
    assert validate_mrp_amount("50").status == "accept"
    assert validate_mrp_amount("-5").status == "reject"
    assert validate_product_name("incl. \u00a2 all taxes").status == "reject"
    assert validate_product_name("GHEE MYSORE PAK").status == "accept"
    assert validate_best_before("see pack").status == "weak"
    assert validate_best_before("6 months").status == "accept"
    assert validate_entity_name("BY").status == "reject"
    assert validate_entity_name("ITC Limited").status == "accept"
    assert validate_contact("care@itc.in").status == "accept"
    assert validate_contact("1800-123-4567").status == "accept"
    assert validate_contact("hello world").status == "weak"
