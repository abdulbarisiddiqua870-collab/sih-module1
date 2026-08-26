from __future__ import annotations

import cv2
import numpy as np

from module1.core.config import settings
from module1.models.schemas import QualityInfo
from module1.preprocessing.images import to_gray


def assess_quality(image: np.ndarray) -> QualityInfo:
    gray = to_gray(image)
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    blur_score = min(1.0, laplacian_variance / 600.0)

    mean_intensity = float(gray.mean())
    brightness_score = max(0.0, 1.0 - abs(mean_intensity - 127.5) / 127.5)

    contrast_score = min(1.0, float(gray.std()) / 64.0)

    height, width = gray.shape[:2]
    resolution_ok = (
        min(height, width) >= settings.min_image_dimension
        and max(height, width) <= settings.max_image_dimension
    )

    score = 0.4 * blur_score + 0.3 * brightness_score + 0.3 * contrast_score
    if not resolution_ok:
        score *= 0.5

    warnings: list[str] = []
    if blur_score < 0.25:
        warnings.append("image appears blurry")
    if brightness_score < 0.35:
        warnings.append("poor lighting conditions")
    if contrast_score < 0.25:
        warnings.append("low contrast")
    if not resolution_ok:
        warnings.append("image resolution outside supported range")

    return QualityInfo(
        score=round(max(0.0, min(1.0, score)), 3),
        blur_score=round(max(0.0, min(1.0, blur_score)), 3),
        brightness_score=round(max(0.0, min(1.0, brightness_score)), 3),
        contrast_score=round(max(0.0, min(1.0, contrast_score)), 3),
        resolution_ok=resolution_ok,
        warnings=warnings,
    )
