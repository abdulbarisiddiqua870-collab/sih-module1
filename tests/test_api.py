from io import BytesIO

from PIL import Image

from module1.core.config import settings
from module1.services.pipeline import pipeline
from tests.conftest import label_png_bytes, requires_tesseract


def test_extract_without_file_fails_validation(client):
    response = client.post("/api/v1/extract")
    assert response.status_code == 422


def test_extract_rejects_empty_file(client):
    response = client.post("/api/v1/extract", files={"file": ("label.png", b"")})
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "EMPTY_FILE"


def test_extract_rejects_unsupported_format(client):
    response = client.post("/api/v1/extract", files={"file": ("notes.txt", b"hello world")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORMAT"


def test_extract_rejects_oversized_file(client):
    payload = b"\x00" * (settings.max_upload_bytes + 1)
    response = client.post("/api/v1/extract", files={"file": ("big.png", payload)})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_extract_rejects_image_dimensions_before_decode(client):
    image_data = BytesIO()
    Image.new("RGB", (settings.max_image_dimension + 1, 1), "white").save(image_data, format="PNG")
    response = client.post("/api/v1/extract", files={"file": ("wide.png", image_data.getvalue())})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_extract_rejects_invalid_image_bytes(client):
    response = client.post("/api/v1/extract", files={"file": ("fake.png", b"this is not an image")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_IMAGE"


def test_extract_returns_structured_error_for_unexpected_runtime_failure(client, monkeypatch):
    class FailingEngine:
        def run(self, _image):
            raise RuntimeError("internal test detail")

    monkeypatch.setattr(pipeline, "_engine", FailingEngine())
    response = client.post("/api/v1/extract", files={"file": ("label.png", label_png_bytes())})
    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "error": {"code": "PROCESSING_ERROR", "message": "Image processing could not be completed"},
    }
    assert "internal test detail" not in response.text


@requires_tesseract
def test_extract_end_to_end_on_synthetic_label(client):
    response = client.post("/api/v1/extract", files={"file": ("label.png", label_png_bytes())})
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["success"] is True
    assert body["image"]["filename"] == "label.png"
    assert body["image"]["width"] > 0
    assert body["metadata"]["processing_time_ms"] > 0
    assert body["raw_ocr_text"]
    assert body["cleaned_ocr_text"]

    fields = body["fields"]
    from module1.models.schemas import KNOWN_FIELDS

    assert set(fields) == KNOWN_FIELDS

    detected = {name for name, field in fields.items() if field["detection_status"] == "detected"}
    for expected in ("mrp", "net_quantity", "manufacture_pack_import_date", "country_of_origin"):
        assert expected in detected, f"{expected} not detected: {fields.get(expected)}"

    mrp = fields["mrp"]
    assert mrp["bounding_box"] is not None and len(mrp["bounding_box"]) == 4
    assert 0.0 <= mrp["confidence"] <= 1.0
    assert mrp["evidence"]

    assert body["unmapped_detections"], "non-declaration text should be preserved"


@requires_tesseract
def test_extract_reports_ocr_metadata(client):
    response = client.post("/api/v1/extract", files={"file": ("label.jpg", label_png_bytes(size=30))})
    assert response.status_code == 200
    metadata = response.json()["metadata"]
    assert metadata["ocr_engine"] == "tesseract"
    assert isinstance(metadata["preprocessing_applied"], list)
