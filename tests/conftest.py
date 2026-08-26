from __future__ import annotations

import shutil
from io import BytesIO

import pytest
import pytesseract
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from module1.main import app
from module1.ocr.engine import OcrEngine


def _detect_tesseract() -> bool:
    try:
        OcrEngine()
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


TESSERACT_AVAILABLE = _detect_tesseract()

requires_tesseract = pytest.mark.skipif(
    not TESSERACT_AVAILABLE,
    reason="tesseract binary not installed on this machine",
)

FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]

LABEL_LINES = [
    "CRISPY POTATO CHIPS",
    "Classic Salted",
    "Manufacturer: SnackWorks Foods Pvt. Ltd.",
    "Plot 42, Industrial Area Phase 2",
    "Noida, Uttar Pradesh 201305",
    "Mfg Date: 08/2026",
    "Best Before: 4 months from packaging",
    "Net Qty: 52 g",
    "MRP: Rs 50.00 (Inclusive of all taxes)",
    "Unit Sale Price: Rs 0.96",
    "Consumer Care: 1800-123-4567",
    "care@snackworks.example",
    "Country of Origin: India",
]


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


def load_font(size: int = 26) -> ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def render_label(
    lines: list[str] | None = None,
    size: int = 26,
    padding: int = 32,
    line_spacing: float = 1.6,
    background: tuple[int, int, int] = (255, 255, 255),
    foreground: tuple[int, int, int] = (15, 15, 15),
):
    lines = LABEL_LINES if lines is None else lines
    font = load_font(size)
    probe = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(probe)
    line_heights = []
    text_widths = []
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        text_widths.append(box[2] - box[0])
        line_heights.append(box[3] - box[1])
    spacing = int(size * line_spacing)
    width = max(text_widths) + padding * 2
    height = spacing * len(lines) + padding * 2
    image = Image.new("RGB", (width, height), background)
    drawer = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        drawer.text((padding, padding + index * spacing), line, fill=foreground, font=font)
    return image


def label_png_bytes(**kwargs) -> bytes:
    buffer = BytesIO()
    render_label(**kwargs).save(buffer, format="PNG")
    return buffer.getvalue()
