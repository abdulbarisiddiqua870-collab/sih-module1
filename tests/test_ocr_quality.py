from __future__ import annotations

import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, "tests")

import module1.ocr.engine as engine_module
from conftest import label_png_bytes
from module1.core.config import settings
from module1.ocr.engine import OcrEngine, solid_word_stats


def bgr_label() -> np.ndarray:
    return cv2.imdecode(np.frombuffer(label_png_bytes(), np.uint8), cv2.IMREAD_COLOR)


def make_dict(lines: list[tuple[str, float]]) -> dict:
    """Build a pytesseract Output.DICT-shaped structure from (text, conf01) rows."""
    out: dict[str, list] = {
        "text": [], "conf": [], "left": [], "top": [], "width": [], "height": [],
        "block_num": [], "par_num": [], "line_num": [],
    }
    for index, (text, conf01) in enumerate(lines):
        words = text.split() or [""]
        for word in words:
            out["text"].append(word)
            out["conf"].append(conf01 * 100)
            out["left"].append(10)
            out["top"].append(10 + index * 30)
            out["width"].append(max(10, len(word) * 8))
            out["height"].append(20)
            out["block_num"].append(1)
            out["par_num"].append(1)
            out["line_num"].append(index + 1)
    return out


class FakeTesseract:
    """Returns scripted results depending on whether the input was upscaled."""

    def __init__(self, base_lines, scaled_lines, alt_psm_lines=None):
        self.base_lines = base_lines
        self.scaled_lines = scaled_lines
        self.alt_psm_lines = alt_psm_lines if alt_psm_lines is not None else scaled_lines
        self.calls: list[tuple[int, str]] = []
        self.string_calls = 0

    def image_to_data(self, img, lang=None, config=None, output_type=None):
        width = img.shape[1]
        self.calls.append((width, config or ""))
        if "--psm 11" in (config or ""):
            return make_dict(self.alt_psm_lines)
        if width > self.base_width:
            return make_dict(self.scaled_lines)
        return make_dict(self.base_lines)

    def image_to_string(self, img, lang=None, config=None):
        self.string_calls += 1
        return "\n".join(text for text, _ in (
            self.alt_psm_lines if "--psm 11" in (config or "") else self.scaled_lines
        )) if img.shape[1] > self.base_width else "\n".join(text for text, _ in self.base_lines)

    def install(self, monkeypatch, base_width):
        self.base_width = base_width
        monkeypatch.setattr(engine_module.pytesseract, "image_to_data", self.image_to_data)
        monkeypatch.setattr(engine_module.pytesseract, "image_to_string", self.image_to_string)


WEAK_BASE = [("junk xx", 0.30)]
STRONG_SCALED = [
    ("Manufacturer SnackWorks Foods", 0.90),
    ("MRP Rs 50", 0.88),
    ("Net Qty 52", 0.92),
    ("Best Before months", 0.85),
    ("Country Origin India", 0.91),
]
WEAK_ALT = [("weak alt", 0.35)]


def test_small_text_escalation_recovers_more_ocr(monkeypatch):
    fake = FakeTesseract(WEAK_BASE, STRONG_SCALED)
    fake.install(monkeypatch, base_width=400)
    image = np.full((300, 400, 3), 255, dtype=np.uint8)

    monkeypatch.setattr(settings, "ocr_escalation_enabled", False)
    off = OcrEngine(orientation_aware=False).run(image)
    monkeypatch.setattr(settings, "ocr_escalation_enabled", True)
    on = OcrEngine(orientation_aware=False).run(image)

    assert solid_word_stats(off.lines)[0] < settings.ocr_escalation_min_solid_words
    assert solid_word_stats(on.lines)[0] >= settings.ocr_escalation_min_solid_words
    assert len(on.cleaned_text) > len(off.cleaned_text)


def test_weak_yield_triggers_exactly_one_escalation_and_early_stops(monkeypatch):
    fake = FakeTesseract(WEAK_BASE, STRONG_SCALED)
    fake.install(monkeypatch, base_width=400)
    image = np.full((300, 400, 3), 255, dtype=np.uint8)

    result = OcrEngine(orientation_aware=False).run(image)

    assert len(fake.calls) == 2
    assert fake.string_calls == 2
    assert result.cleaned_text.count("SnackWorks") == 1


def test_third_pass_alt_psm_when_second_still_weak(monkeypatch):
    fake = FakeTesseract(WEAK_BASE, WEAK_BASE, alt_psm_lines=STRONG_SCALED)
    fake.install(monkeypatch, base_width=400)
    image = np.full((300, 400, 3), 255, dtype=np.uint8)

    result = OcrEngine(orientation_aware=False).run(image)

    assert len(fake.calls) == 3
    assert "--psm 11" in fake.calls[-1][1]
    assert "SnackWorks" in result.cleaned_text


def test_strong_yield_never_escalates(monkeypatch):
    strong_base = STRONG_SCALED
    fake = FakeTesseract(strong_base, [])
    fake.install(monkeypatch, base_width=400)
    image = np.full((300, 400, 3), 255, dtype=np.uint8)

    OcrEngine(orientation_aware=False).run(image)

    assert len(fake.calls) == 1


def test_winner_selection_highest_solid_then_confidence(monkeypatch):
    medium_scaled = [("alpha beta gamma delta", 0.70)]
    higher_conf_same_count = [("alpha beta gamma delta", 0.95)]
    fake = FakeTesseract(WEAK_BASE, medium_scaled, alt_psm_lines=higher_conf_same_count)
    fake.install(monkeypatch, base_width=400)
    image = np.full((300, 400, 3), 255, dtype=np.uint8)

    result = OcrEngine(orientation_aware=False).run(image)

    assert len(fake.calls) == 3
    assert solid_word_stats(result.lines) == (4, round(0.95, 3))


def test_escalated_pass_config_uses_dpi_hint_and_upscale(monkeypatch):
    fake = FakeTesseract(WEAK_BASE, STRONG_SCALED)
    fake.install(monkeypatch, base_width=400)
    image = np.full((300, 400, 3), 255, dtype=np.uint8)

    OcrEngine(orientation_aware=False).run(image)

    width, config = fake.calls[1]
    assert width == 800
    assert f"user_defined_dpi={settings.ocr_dpi_hint}" in config
    assert "--psm 3" in config


def test_escalated_bbox_coordinates_mapped_to_original_frame(monkeypatch):
    lines_at_scale = [("Manufacturer SnackWorks Foods Limited", 0.9)]
    fake = FakeTesseract(WEAK_BASE, lines_at_scale)
    fake.install(monkeypatch, base_width=400)
    image = np.full((300, 400, 3), 255, dtype=np.uint8)

    result = OcrEngine(orientation_aware=False).run(image)

    assert len(result.lines) == 1
    x1, y1, x2, y2 = result.lines[0].bounding_box
    assert 0 <= x1 < x2 <= 400
    assert 0 <= y1 < y2 <= 300


def test_real_tesseract_tiny_image_never_worse_with_escalation():
    base = bgr_label()
    tiny = cv2.resize(base, None, fx=0.22, fy=0.22, interpolation=cv2.INTER_CUBIC)
    off = OcrEngine(orientation_aware=False).run(tiny)
    on = OcrEngine(orientation_aware=False).run(tiny)
    assert solid_word_stats(on.lines)[0] >= solid_word_stats(off.lines)[0]


def test_real_tesseract_healthy_image_runs_single_pass(monkeypatch):
    calls = {"n": 0}
    original = engine_module.pytesseract.image_to_data

    def counting(img, **kwargs):
        calls["n"] += 1
        return original(img, **kwargs)

    monkeypatch.setattr(engine_module.pytesseract, "image_to_data", counting)
    OcrEngine(orientation_aware=False).run(bgr_label())
    assert calls["n"] == 1
