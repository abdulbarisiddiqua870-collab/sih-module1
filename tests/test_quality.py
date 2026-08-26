import cv2
import numpy as np
import pytest

from module1.models.schemas import QualityInfo
from module1.preprocessing.quality import assess_quality
from tests.conftest import label_png_bytes


def to_bgr(png_bytes: bytes) -> np.ndarray:
    import cv2

    array = np.frombuffer(png_bytes, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def test_returns_quality_info_model():
    quality = assess_quality(to_bgr(label_png_bytes()))
    assert isinstance(quality, QualityInfo)
    assert 0.0 <= quality.score <= 1.0
    assert 0.0 <= quality.blur_score <= 1.0
    assert 0.0 <= quality.brightness_score <= 1.0
    assert 0.0 <= quality.contrast_score <= 1.0


def test_sharp_image_scores_higher_blur_than_blurred():
    sharp = to_bgr(label_png_bytes())
    blurred = cv2.GaussianBlur(sharp, (0, 0), sigmaX=9)
    sharp_score = assess_quality(sharp).blur_score
    blurred_score = assess_quality(blurred).blur_score
    assert sharp_score > blurred_score
    assert "image appears blurry" in assess_quality(blurred).warnings


def test_dark_image_flags_lighting():
    dark = (to_bgr(label_png_bytes()) * 0.15).astype(np.uint8)
    quality = assess_quality(dark)
    assert quality.brightness_score < 0.4
    assert "poor lighting conditions" in quality.warnings


def test_flat_image_has_low_contrast_and_low_score():
    flat = np.full((400, 400, 3), 128, dtype=np.uint8)
    quality = assess_quality(flat)
    assert quality.contrast_score < 0.05
    assert "low contrast" in quality.warnings


def test_small_image_resolution_flagged():
    tiny = np.full((60, 60, 3), 200, dtype=np.uint8)
    quality = assess_quality(tiny)
    assert quality.resolution_ok is False
    assert any("resolution" in warning for warning in quality.warnings)
