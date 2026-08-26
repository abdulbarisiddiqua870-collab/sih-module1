import pytest

from module1.models.schemas import (
    BEST_BEFORE_USE_BY,
    COMMON_OR_GENERIC_NAME,
    CONSUMER_CARE,
    COUNTRY_OF_ORIGIN,
    MANUFACTURER_ADDRESS,
    MANUFACTURER_NAME,
    MANUFACTURE_PACK_IMPORT_DATE,
    MRP,
    NET_QUANTITY,
    PACKER_NAME,
    PRODUCT_NAME,
    UNIT_SALE_PRICE,
    KNOWN_FIELDS,
    DetectionStatus,
)
from module1.extraction.parser import extract_fields
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


def make_result(lines: list[OcrLine], raw: str | None = None) -> OcrResult:
    text = raw if raw is not None else "\n".join(line.text for line in lines)
    return OcrResult(raw_text=text, cleaned_text=text, lines=lines)


def test_empty_ocr_yields_all_fields_not_detected():
    fields, unmapped = extract_fields(make_result([]), image_height_px=1000)
    assert set(fields) == KNOWN_FIELDS
    assert all(f.detection_status == DetectionStatus.NOT_DETECTED for f in fields.values())
    assert fields[MRP].confidence == 0.0
    assert fields[MRP].value is None
    assert unmapped == []


def test_mrp_detected_with_geometry():
    line = make_line("MRP: Rs 50.00 (Inclusive of all taxes)", y=400)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    result = fields[MRP]
    assert result.value == "50.00"
    assert result.detection_status == DetectionStatus.DETECTED
    assert "MRP" in result.evidence
    assert result.bounding_box == [40, 400, 40 + len(line.text) * 12, 424]
    assert result.region_width_px == result.bounding_box[2] - result.bounding_box[0]
    assert result.char_height_px == 24


def test_net_quantity_normalized():
    line = make_line("Net Qty: 52 g", y=300)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    assert fields[NET_QUANTITY].value == "52 g"
    assert fields[NET_QUANTITY].detection_status == DetectionStatus.DETECTED


def test_manufacture_date_from_keyword_line():
    line = make_line("Mfg Date: 08/2026", y=200)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    assert fields[MANUFACTURE_PACK_IMPORT_DATE].value == "08/2026"
    assert fields[MANUFACTURE_PACK_IMPORT_DATE].detection_status == DetectionStatus.DETECTED


def test_best_before_captured():
    line = make_line("Best Before: 4 months from packaging", y=500)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    assert "4 months" in fields[BEST_BEFORE_USE_BY].value
    assert fields[BEST_BEFORE_USE_BY].detection_status == DetectionStatus.DETECTED


@pytest.mark.parametrize("text", ["Best Before: MRP", "Best Before: Net Weight 2009"])
def test_best_before_without_date_or_duration_is_not_detected(text):
    fields, _ = extract_fields(make_result([make_line(text, y=500)]), image_height_px=1000)
    assert fields[BEST_BEFORE_USE_BY].detection_status != DetectionStatus.DETECTED


def test_best_before_uses_nearby_valid_value():
    lines = [make_line("Best Before:", y=500), make_line("6 months from packaging", y=530)]
    fields, _ = extract_fields(make_result(lines), image_height_px=1000)
    assert fields[BEST_BEFORE_USE_BY].value == "6 months from packaging"
    assert fields[BEST_BEFORE_USE_BY].detection_status == DetectionStatus.DETECTED


def test_best_before_does_not_use_distant_value():
    lines = [make_line("Best Before:", y=100), make_line("6 months from packaging", y=500)]
    fields, _ = extract_fields(make_result(lines), image_height_px=1000)
    assert fields[BEST_BEFORE_USE_BY].detection_status == DetectionStatus.NOT_DETECTED


def test_country_of_origin():
    line = make_line("Country of Origin: India", y=600)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    assert fields[COUNTRY_OF_ORIGIN].value == "India"


def test_unit_sale_price():
    line = make_line("Unit Sale Price: Rs 0.96", y=700)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    assert fields[UNIT_SALE_PRICE].value == "0.96"


def test_consumer_care_phone_same_line():
    line = make_line("Consumer Care: 1800-123-4567", y=800)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    assert fields[CONSUMER_CARE].value == "1800-123-4567"


def test_consumer_care_email_on_next_line():
    key_line = make_line("Consumer Care:", y=800)
    email_line = make_line("care@snackworks.example", y=830)
    fields, _ = extract_fields(make_result([key_line, email_line]), image_height_px=1000)
    assert fields[CONSUMER_CARE].value == "care@snackworks.example"
    assert "Consumer Care:" in fields[CONSUMER_CARE].evidence


def test_manufacturer_name_and_multiline_address():
    name_line = make_line("Manufacturer: SnackWorks Foods Pvt. Ltd.", y=100)
    addr1 = make_line("Plot 42, Industrial Area Phase 2", y=130)
    addr2 = make_line("Noida, Uttar Pradesh 201305", y=160)
    date_line = make_line("Mfg Date: 08/2026", y=190)
    fields, _ = extract_fields(make_result([name_line, addr1, addr2, date_line]), image_height_px=1000)
    assert fields[MANUFACTURER_NAME].value == "SnackWorks Foods Pvt. Ltd."
    assert fields[MANUFACTURER_ADDRESS].value is not None
    assert "Plot 42" in fields[MANUFACTURER_ADDRESS].value
    assert "201305" in fields[MANUFACTURER_ADDRESS].value


def test_combined_manufacturer_and_packer_label_extracts_entity_name():
    line = make_line("Manufactured and Packed By: Example Foods Ltd.", y=100)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    assert fields[MANUFACTURER_NAME].value == "Example Foods Ltd."
    assert fields[PACKER_NAME].value == "Example Foods Ltd."


def test_entity_role_fragment_is_not_a_manufacturer_name():
    line = make_line("Manufactured & Packed By", y=100)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    assert fields[MANUFACTURER_NAME].detection_status == DetectionStatus.NOT_DETECTED


def test_regulatory_entity_text_is_not_a_company_name():
    line = make_line("Packed Commodities Rules 2011", y=100)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    assert fields[PACKER_NAME].detection_status == DetectionStatus.NOT_DETECTED


def test_low_confidence_field_marked_uncertain():
    line = make_line("MRP: Rs 50.00", y=400, conf=0.35)
    fields, _ = extract_fields(make_result([line]), image_height_px=1000)
    assert fields[MRP].detection_status == DetectionStatus.UNCERTAIN


def test_product_name_prefers_uppercase_top_line_and_generic_alias_set():
    title = make_line("CRISPY POTATO CHIPS", y=20)
    subtitle = make_line("Classic Salted", y=50)
    fields, unmapped = extract_fields(make_result([title, subtitle]), image_height_px=1000)
    assert fields[PRODUCT_NAME].value == "CRISPY POTATO CHIPS"
    assert COMMON_OR_GENERIC_NAME in fields
    assert "Classic Salted" in [d.text for d in unmapped]


def test_unmapped_regions_capture_unknown_text():
    known = make_line("MRP: Rs 90.00", y=400)
    mystery = make_line("Batch Code ZZ-9911", y=700, width=200)
    fields, unmapped = extract_fields(make_result([known, mystery]), image_height_px=1000)
    texts = [d.text for d in unmapped]
    assert "Batch Code ZZ-9911" in texts
    assert all(d.bounding_box is not None and len(d.bounding_box) == 4 for d in unmapped)


def test_full_synthetic_label_pipeline_parse():
    lines = [
        make_line("CRISPY POTATO CHIPS", y=30),
        make_line("Classic Salted", y=70),
        make_line("Manufacturer: SnackWorks Foods Pvt. Ltd.", y=110),
        make_line("Plot 42, Industrial Area Phase 2", y=140),
        make_line("Noida, Uttar Pradesh 201305", y=170),
        make_line("Mfg Date: 08/2026", y=210),
        make_line("Best Before: 4 months from packaging", y=250),
        make_line("Net Qty: 52 g", y=290),
        make_line("MRP: Rs 50.00 (Inclusive of all taxes)", y=330),
        make_line("Unit Sale Price: Rs 0.96", y=370),
        make_line("Consumer Care: 1800-123-4567", y=410),
        make_line("care@snackworks.example", y=440),
        make_line("Country of Origin: India", y=480),
    ]
    fields, unmapped = extract_fields(make_result(lines), image_height_px=520)
    detected = {name for name, f in fields.items() if f.detection_status == DetectionStatus.DETECTED}
    for expected in (
        PRODUCT_NAME,
        MANUFACTURER_NAME,
        MANUFACTURE_PACK_IMPORT_DATE,
        BEST_BEFORE_USE_BY,
        NET_QUANTITY,
        MRP,
        UNIT_SALE_PRICE,
        CONSUMER_CARE,
        COUNTRY_OF_ORIGIN,
    ):
        assert expected in detected, f"{expected} not detected"
    assert any("Classic Salted" in d.text for d in unmapped)
