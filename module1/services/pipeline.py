from __future__ import annotations

import time
from io import BytesIO
from pathlib import Path

import pytesseract

from module1.core.config import settings
from module1.core.errors import ErrorCode, PipelineError
from module1.extraction.parser import extract_fields
from module1.models.schemas import ExtractionResponse, ImageInfo, MetadataInfo
from module1.ocr.engine import OcrEngine
from module1.preprocessing.images import decode_image, preprocess
from module1.preprocessing.quality import assess_quality


class ExtractionPipeline:
    def __init__(self) -> None:
        self._engine: OcrEngine | None = None

    @property
    def engine(self) -> OcrEngine:
        if self._engine is None:
            self._engine = OcrEngine()
        return self._engine

    def run(self, data: bytes, filename: str) -> ExtractionResponse:
        started = time.perf_counter()
        self._validate_upload(data, filename)

        original = decode_image(data)
        if original is None:
            raise PipelineError(ErrorCode.INVALID_IMAGE, "File bytes could not be decoded as an image")

        quality = assess_quality(original)
        processed, operations = preprocess(original)

        try:
            ocr_result = self.engine.run(processed)
        except pytesseract.TesseractNotFoundError as exc:
            raise PipelineError(
                ErrorCode.OCR_UNAVAILABLE,
                "Tesseract OCR engine is not installed or not on PATH. "
                f"Install the tesseract binary and retry. Detail: {exc}",
            ) from exc

        fields, unmapped = extract_fields(ocr_result, image_height_px=processed.shape[0])
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

        return ExtractionResponse(
            image=self._image_info(data, filename, original),
            quality=quality,
            fields=fields,
            unmapped_detections=unmapped,
            raw_ocr_text=ocr_result.raw_text,
            cleaned_ocr_text=ocr_result.cleaned_text,
            metadata=MetadataInfo(
                ocr_engine=settings.ocr_engine,
                preprocessing_applied=operations,
                processing_time_ms=elapsed_ms,
            ),
        )

    def _validate_upload(self, data: bytes, filename: str) -> None:
        if not data:
            raise PipelineError(ErrorCode.EMPTY_FILE, "Uploaded file is empty")
        suffix = Path(filename).suffix.lower()
        if not suffix or suffix not in settings.allowed_extensions:
            allowed = ", ".join(sorted(settings.allowed_extensions))
            raise PipelineError(
                ErrorCode.UNSUPPORTED_FORMAT,
                f"Unsupported file type '{suffix or 'unknown'}'. Allowed: {allowed}",
            )
        if len(data) > settings.max_upload_bytes:
            max_mb = settings.max_upload_bytes // (1024 * 1024)
            raise PipelineError(ErrorCode.FILE_TOO_LARGE, f"File exceeds the {max_mb} MB upload limit")

    def _image_info(self, data: bytes, filename: str, image) -> ImageInfo:
        height, width = image.shape[:2]
        dpi = self._read_dpi(data)
        return ImageInfo(
            filename=Path(filename).name,
            width=int(width),
            height=int(height),
            format=Path(filename).suffix.lstrip(".").upper() or "UNKNOWN",
            dpi=dpi,
        )

    def _read_dpi(self, data: bytes) -> float | None:
        try:
            from PIL import Image

            with Image.open(BytesIO(data)) as pil_image:
                dpi = pil_image.info.get("dpi")
                if dpi:
                    return round(sum(float(value) for value in dpi) / len(dpi), 2)
        except Exception:
            return None
        return None


pipeline = ExtractionPipeline()
