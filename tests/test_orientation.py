import cv2
import numpy as np
import pytest

from module1.ocr.engine import OcrEngine
from module1.ocr.orientation import detect_orientation, map_bbox_to_original, rotate_image
from tests.conftest import label_png_bytes, requires_tesseract

FORWARD_TRANSFORMS = {
    90: lambda b, w, h: [h - b[3], b[0], h - b[1], b[2]],
    180: lambda b, w, h: [w - b[2], h - b[3], w - b[0], h - b[1]],
    270: lambda b, w, h: [b[1], w - b[2], b[3], w - b[0]],
}


def base_image() -> np.ndarray:
    return cv2.imdecode(np.frombuffer(label_png_bytes(), np.uint8), cv2.IMREAD_COLOR)


@pytest.mark.parametrize("degrees", [0, 90, 180, 270])
def test_bbox_mapping_roundtrip(degrees):
    width, height = 640, 480
    original = [37, 51, 402, 300]
    if degrees == 0:
        forward = original
    else:
        forward = FORWARD_TRANSFORMS[degrees](original, width, height)
    restored = map_bbox_to_original(forward, degrees, width, height)
    assert restored == original


def test_rotate_image_dimensions():
    image = base_image()
    height, width = image.shape[:2]
    assert rotate_image(image, 0).shape[:2] == (height, width)
    assert rotate_image(image, 90).shape[:2] == (width, height)
    assert rotate_image(image, 180).shape[:2] == (height, width)
    assert rotate_image(image, 270).shape[:2] == (width, height)
    assert np.array_equal(rotate_image(rotate_image(image, 90), 270), image)


@requires_tesseract
@pytest.mark.parametrize("degrees", [0, 90, 180, 270])
def test_detect_orientation_all_rotations(degrees):
    rotated = rotate_image(base_image(), degrees)
    assert detect_orientation(rotated, lang="eng", psm=3) == (360 - degrees) % 360


@requires_tesseract
@pytest.mark.parametrize("degrees", [0, 90, 180, 270])
def test_engine_reads_text_at_all_rotations(degrees):
    base = base_image()
    rotated = rotate_image(base, degrees)
    result = OcrEngine().run(rotated)
    combined = result.cleaned_text
    assert "MRP" in combined
    assert "50.00" in combined
    assert result.rotation_applied == (360 - degrees) % 360
    rotated_height, rotated_width = rotated.shape[:2]
    for line in result.lines:
        x1, y1, x2, y2 = line.bounding_box
        assert 0 <= x1 < x2 <= rotated_width
        assert 0 <= y1 < y2 <= rotated_height


@requires_tesseract
def test_engine_upright_bbox_matches_no_rotation_baseline():
    base = base_image()
    baseline = OcrEngine(orientation_aware=False).run(base)
    aware = OcrEngine(orientation_aware=True).run(base)
    assert aware.rotation_applied == 0
    baseline_boxes = sorted(l.bounding_box for l in baseline.lines if "MRP" in l.text)
    aware_boxes = sorted(l.bounding_box for l in aware.lines if "MRP" in l.text)
    assert baseline_boxes == aware_boxes


@requires_tesseract
def test_pipeline_extracts_from_rotated_upload(client):
    rotated_png_buffer = __import__("io").BytesIO()
    __import__("PIL.Image", fromlist=["Image"]).fromarray(
        cv2.cvtColor(rotate_image(base_image(), 90), cv2.COLOR_BGR2RGB)
    ).save(rotated_png_buffer, format="PNG")
    response = client.post(
        "/api/v1/extract",
        files={"file": ("rotated.png", rotated_png_buffer.getvalue())},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    detected = {k for k, v in body["fields"].items() if v["detection_status"] == "detected"}
    assert "mrp" in detected
    width, height = body["image"]["width"], body["image"]["height"]
    box = body["fields"]["mrp"]["bounding_box"]
    assert box is not None
    assert 0 <= box[0] < box[2] <= width
    assert 0 <= box[1] < box[3] <= height
