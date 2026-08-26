from __future__ import annotations

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

ROTATION_SCORE_MARGIN = 2.0
PRIMARY_ORIENTATION_PSM = 3
SECONDARY_ORIENTATION_PSM = 11


def rotate_image(image: np.ndarray, degrees_cw: int) -> np.ndarray:
    degrees_cw %= 360
    if degrees_cw == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if degrees_cw == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if degrees_cw == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def map_bbox_to_original(bbox: list[int], degrees_cw: int, original_width: int, original_height: int) -> list[int]:
    degrees_cw %= 360
    x1, y1, x2, y2 = bbox
    if degrees_cw == 90:
        return [int(y1), int(original_height - x2), int(y2), int(original_height - x1)]
    if degrees_cw == 180:
        return [
            int(original_width - x2),
            int(original_height - y2),
            int(original_width - x1),
            int(original_height - y1),
        ]
    if degrees_cw == 270:
        return [int(original_width - y2), int(x1), int(original_width - y1), int(x2)]
    return [int(x1), int(y1), int(x2), int(y2)]


def _downscale_for_probe(image: np.ndarray, max_side: int) -> np.ndarray:
    height, width = image.shape[:2]
    scale = max_side / float(max(height, width))
    if scale >= 1.0:
        return image
    return cv2.resize(image, (max(1, int(width * scale)), max(1, int(height * scale))), interpolation=cv2.INTER_AREA)


def osd_rotation(small_image: np.ndarray, min_confidence: float) -> tuple[int, float] | None:
    try:
        osd = pytesseract.image_to_osd(small_image, output_type=Output.DICT)
    except Exception:
        return None
    try:
        degrees = int(osd.get("rotate") or 0) % 360
        confidence = float(osd.get("orientation_conf") or 0.0)
    except (TypeError, ValueError):
        return None
    return degrees, confidence


def score_orientation(small_image: np.ndarray, degrees_cw: int, lang: str, config: str) -> float:
    rotated = rotate_image(small_image, degrees_cw)
    try:
        data = pytesseract.image_to_data(rotated, lang=lang, config=config, output_type=Output.DICT)
    except Exception:
        return 0.0
    score = 0.0
    for index in range(len(data["text"])):
        text = (data["text"][index] or "").strip()
        try:
            conf = float(data["conf"][index])
        except (TypeError, ValueError):
            continue
        if len(text) < 2 or conf < 0:
            continue
        alpha_ratio = sum(ch.isalpha() for ch in text) / len(text)
        if alpha_ratio < 0.5:
            continue
        score += conf * min(len(text), 12)
    return score


def detect_orientation(
    image: np.ndarray,
    lang: str,
    psm: int,
    min_osd_confidence: float = 2.5,
    probe_max_side: int = 600,
) -> int:
    small = _downscale_for_probe(image, probe_max_side)

    osd = osd_rotation(small, min_osd_confidence)
    osd_degrees, osd_confidence = osd if osd is not None else (None, 0.0)
    if osd_degrees is not None and osd_confidence >= min_osd_confidence:
        return osd_degrees

    candidates = (0, 90, 180, 270)

    def scores_for_psm(probe_psm: int) -> dict[int, float]:
        config = f"--oem 3 --psm {probe_psm}"
        return {
            candidate: score_orientation(small, candidate, lang, config)
            for candidate in candidates
        }

    primary_scores = scores_for_psm(PRIMARY_ORIENTATION_PSM)
    primary_best = max(primary_scores, key=lambda c: (primary_scores[c], -c))
    primary_is_strong = (
        primary_scores[primary_best]
        >= ROTATION_SCORE_MARGIN
        * max(max(score for candidate, score in primary_scores.items() if candidate != primary_best), 1.0)
    )
    if primary_is_strong:
        return primary_best

    secondary_scores = scores_for_psm(SECONDARY_ORIENTATION_PSM)
    secondary_best = max(secondary_scores, key=lambda c: (secondary_scores[c], -c))
    secondary_is_strong = (
        secondary_best != 0
        and secondary_scores[secondary_best] >= ROTATION_SCORE_MARGIN * max(secondary_scores[0], 1.0)
    )
    if secondary_is_strong:
        return secondary_best

    if primary_best != 0:
        if osd_degrees == 0:
            return 0
        if primary_scores[primary_best] < ROTATION_SCORE_MARGIN * max(primary_scores[0], 1.0):
            return 0
        return primary_best
    if osd_degrees is not None:
        return osd_degrees
    return 0
