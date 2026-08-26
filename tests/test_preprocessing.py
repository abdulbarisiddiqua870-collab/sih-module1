import cv2
import numpy as np
import pytest

from module1.core.config import settings
from module1.preprocessing.images import (
    decode_image,
    deskew,
    enforce_bounds,
    measure_skew,
    preprocess,
)
from tests.conftest import label_png_bytes, render_label


def bgr_from_png(data: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)


def bgr_from_pil(pil_image) -> np.ndarray:
    return cv2.cvtColor(np.array(pil_image.convert("RGB")), cv2.COLOR_RGB2BGR)


def test_decode_invalid_bytes_returns_none():
    assert decode_image(b"not-an-image") is None


def test_decode_valid_png():
    image = decode_image(label_png_bytes())
    assert image is not None
    assert image.ndim == 3


def test_enforce_bounds_downscales_large(monkeypatch):
    monkeypatch.setattr(settings, "max_image_dimension", 100)
    big = np.full((600, 900, 3), 255, dtype=np.uint8)
    out = enforce_bounds(big)
    assert max(out.shape[:2]) == 100


def test_enforce_bounds_upscales_small(monkeypatch):
    monkeypatch.setattr(settings, "min_image_dimension", 300)
    small = np.full((50, 80, 3), 255, dtype=np.uint8)
    out = enforce_bounds(small)
    assert min(out.shape[:2]) >= 300


def test_measure_skew_detects_rotation():
    straight = bgr_from_pil(render_label(lines=["THE QUICK BROWN FOX"], size=40))
    height, width = straight.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), 5.0, 1.0)
    rotated = cv2.warpAffine(straight, matrix, (width, height), borderValue=(255, 255, 255))
    assert abs(measure_skew(rotated)) > abs(measure_skew(straight))


def test_deskew_reduces_skew():
    straight = bgr_from_pil(render_label(lines=["THE QUICK BROWN FOX JUMPS"], size=40))
    height, width = straight.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), 5.0, 1.0)
    rotated = cv2.warpAffine(straight, matrix, (width, height), borderValue=(255, 255, 255))
    corrected, applied = deskew(rotated)
    assert applied != 0.0
    assert abs(measure_skew(corrected)) < abs(measure_skew(rotated))


def test_deskew_ignores_straight_image():
    straight = bgr_from_pil(render_label(lines=["FLAT LINE TEXT HERE"], size=40))
    _, applied = deskew(straight)
    assert applied == 0.0


def test_preprocess_reports_operations(monkeypatch):
    image = bgr_from_png(label_png_bytes())
    out, ops = preprocess(image)
    assert out is not None
    for expected in ("denoise", "clahe", "sharpen"):
        assert expected in ops

    for flag in ("apply_denoise", "apply_clahe", "apply_sharpen", "apply_deskew"):
        monkeypatch.setattr(settings, flag, False)
    _, ops_off = preprocess(image)
    assert ops_off == []
