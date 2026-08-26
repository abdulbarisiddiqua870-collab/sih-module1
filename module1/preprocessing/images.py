from __future__ import annotations

import cv2
import numpy as np

from module1.core.config import settings


def decode_image(data: bytes) -> np.ndarray | None:
    array = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(array, cv2.IMREAD_COLOR)


def enforce_bounds(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    longest = max(height, width)
    shortest = min(height, width)
    scale = 1.0
    if longest > settings.max_image_dimension:
        scale = settings.max_image_dimension / longest
    elif shortest < settings.min_image_dimension:
        scale = settings.min_image_dimension / shortest
    if scale == 1.0:
        return image
    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    return cv2.resize(image, (max(1, int(width * scale)), max(1, int(height * scale))), interpolation=interpolation)


def to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def denoise(image: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(image, None, 5, 5, 7, 21)


def apply_clahe(image: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lightness = clahe.apply(lightness)
    merged = cv2.merge((lightness, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def sharpen(image: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=3)
    return cv2.addWeighted(image, 1.5, blurred, -0.5, 0)


def measure_skew(image: np.ndarray) -> float:
    gray = to_gray(image)
    binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = cv2.findNonZero(binary)
    if coords is None:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    if angle <= -45.0:
        angle += 90.0
    elif angle >= 45.0:
        angle -= 90.0
    return -float(angle)


def deskew(image: np.ndarray, min_angle: float = 0.3, max_angle: float = 15.0) -> tuple[np.ndarray, float]:
    skew = measure_skew(image)
    if abs(skew) < min_angle or abs(skew) > max_angle:
        return image, 0.0
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), -skew, 1.0)
    corrected = cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    return corrected, round(-skew, 2)


def preprocess(image: np.ndarray) -> tuple[np.ndarray, list[str]]:
    out = enforce_bounds(image)
    operations: list[str] = []
    if settings.apply_denoise:
        out = denoise(out)
        operations.append("denoise")
    if settings.apply_clahe:
        out = apply_clahe(out)
        operations.append("clahe")
    if settings.apply_sharpen:
        out = sharpen(out)
        operations.append("sharpen")
    if settings.apply_deskew:
        out, applied = deskew(out)
        if applied:
            operations.append("deskew")
    return out, operations
