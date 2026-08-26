from __future__ import annotations

from dataclasses import dataclass
from statistics import median

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

from module1.core.config import settings
from module1.ocr.orientation import detect_orientation, map_bbox_to_original, rotate_image
from module1.ocr.text import clean_text

ALT_ESCALATION_PSM = 11


@dataclass
class OcrWord:
    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int


@dataclass
class OcrLine:
    text: str
    confidence: float
    bounding_box: list[int]
    char_height_px: int


@dataclass
class OcrResult:
    raw_text: str
    cleaned_text: str
    lines: list[OcrLine]
    rotation_applied: int = 0


def is_tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def solid_word_stats(lines: list[OcrLine]) -> tuple[int, float]:
    """Count confidently recognized alphabetic words and their mean confidence.

    A word counts as solid when it has at least 3 characters, is majority
    alphabetic, and its line confidence is at least 0.6.
    """
    solid = 0
    confidences: list[float] = []
    for line in lines:
        if line.confidence < 0.6:
            continue
        for token in line.text.split():
            if len(token) < 3:
                continue
            alpha = sum(ch.isalpha() for ch in token)
            if alpha >= max(2, int(len(token) * 0.6)):
                solid += 1
                confidences.append(line.confidence)
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return solid, round(mean_conf, 3)


class OcrEngine:
    def __init__(self, lang: str | None = None, psm: int | None = None, orientation_aware: bool | None = None) -> None:
        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        self.lang = lang or settings.tesseract_lang
        self.psm = psm or settings.tesseract_psm
        self.orientation_aware = settings.ocr_orientation_aware if orientation_aware is None else orientation_aware

    def run(self, image: np.ndarray) -> OcrResult:
        rotation = 0
        working = image
        if self.orientation_aware:
            rotation = detect_orientation(
                image,
                lang=self.lang,
                psm=self.psm,
                min_osd_confidence=settings.osd_min_confidence,
                probe_max_side=settings.orientation_probe_max_side,
            )
            if rotation:
                working = rotate_image(image, rotation)

        best = self._execute_pass(working, rotation=rotation)
        best_solid, _best_conf = solid_word_stats(best.lines)

        if settings.ocr_escalation_enabled and best_solid < settings.ocr_escalation_min_solid_words:
            candidates = [best]
            for scale, psm in (
                (settings.ocr_escalation_scale, self.psm),
                (settings.ocr_escalation_scale, ALT_ESCALATION_PSM),
            ):
                candidate = self._execute_pass(
                    working,
                    rotation=rotation,
                    scale=scale,
                    psm=psm,
                    dpi=settings.ocr_dpi_hint,
                )
                candidates.append(candidate)
                candidate_solid, _ = solid_word_stats(candidate.lines)
                if candidate_solid >= settings.ocr_escalation_min_solid_words:
                    break
            best = max(candidates, key=lambda r: (solid_word_stats(r.lines)[0], solid_word_stats(r.lines)[1]))
        return best

    def _execute_pass(
        self,
        working: np.ndarray,
        rotation: int = 0,
        scale: float = 1.0,
        psm: int | None = None,
        dpi: int | None = None,
    ) -> OcrResult:
        source = working
        if scale != 1.0:
            source = cv2.resize(working, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        rgb = cv2.cvtColor(source, cv2.COLOR_BGR2RGB) if source.ndim == 3 else source
        config = f"--oem 3 --psm {psm or self.psm}"
        if dpi:
            config += f" -c user_defined_dpi={dpi}"
        data = pytesseract.image_to_data(rgb, lang=self.lang, config=config, output_type=Output.DICT)
        raw = pytesseract.image_to_string(rgb, lang=self.lang, config=config)

        lines = self._group_lines(data)
        if scale != 1.0:
            lines = [
                OcrLine(
                    text=line.text,
                    confidence=line.confidence,
                    bounding_box=[
                        int(round(line.bounding_box[0] / scale)),
                        int(round(line.bounding_box[1] / scale)),
                        int(round(line.bounding_box[2] / scale)),
                        int(round(line.bounding_box[3] / scale)),
                    ],
                    char_height_px=max(1, int(round(line.char_height_px / scale))),
                )
                for line in lines
            ]
        if rotation:
            original_height, original_width = image_shape_of(working)
            mapped_working_width = original_width
            mapped_working_height = original_height
            if rotation in (90, 270):
                mapped_working_width, mapped_working_height = original_height, original_width
            lines = [
                OcrLine(
                    text=line.text,
                    confidence=line.confidence,
                    bounding_box=map_bbox_to_original(
                        line.bounding_box,
                        rotation,
                        mapped_working_width,
                        mapped_working_height,
                    ),
                    char_height_px=line.char_height_px,
                )
                for line in lines
            ]
        cleaned = clean_text("\n".join(line.text for line in lines)) or clean_text(raw)
        return OcrResult(raw_text=raw.strip(), cleaned_text=cleaned, lines=lines, rotation_applied=rotation)

    def _group_lines(self, data: dict) -> list[OcrLine]:
        grouped: dict[tuple[int, int, int], list[OcrWord]] = {}
        for index in range(len(data["text"])):
            text = (data["text"][index] or "").strip()
            try:
                conf = float(data["conf"][index])
            except (TypeError, ValueError):
                continue
            if not text or conf < 0:
                continue
            key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
            grouped.setdefault(key, []).append(
                OcrWord(
                    text=text,
                    confidence=conf / 100.0,
                    x=int(data["left"][index]),
                    y=int(data["top"][index]),
                    width=int(data["width"][index]),
                    height=int(data["height"][index]),
                )
            )

        lines: list[OcrLine] = []
        for words in grouped.values():
            if not words:
                continue
            text = " ".join(word.text for word in words)
            x1 = min(w.x for w in words)
            y1 = min(w.y for w in words)
            x2 = max(w.x + w.width for w in words)
            y2 = max(w.y + w.height for w in words)
            confidence = sum(w.confidence for w in words) / len(words)
            char_height = max(1, int(median(w.height for w in words)))
            lines.append(
                OcrLine(text=text, confidence=confidence, bounding_box=[x1, y1, x2, y2], char_height_px=char_height)
            )
        return lines


def image_shape_of(image: np.ndarray) -> tuple[int, int]:
    height, width = image.shape[:2]
    return height, width
