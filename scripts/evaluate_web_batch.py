from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from module1.ocr.engine import solid_word_stats
from module1.services.pipeline import ExtractionPipeline


FIELDS = (
    "product_name",
    "common_or_generic_name",
    "net_quantity",
    "mrp",
    "manufacture_pack_import_date",
    "best_before_use_by",
    "manufacturer_name",
    "manufacturer_address",
    "consumer_care",
)

DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/.-]\d{1,2}[/.-](?:\d{2}|20\d{2})|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[ ./-]?(?:\d{2}|20\d{2})|"
    r"\d{1,2}[/.-]20\d{2})\b",
    re.IGNORECASE,
)
MRP_RE = re.compile(r"\bm\s*[.]?\s*r\s*[.]?\s*p\b|\bmrp\b|\brs\.?\s*\d", re.IGNORECASE)
QUANTITY_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:kg|kgs|g|gm|gms|grams?|ml|millilit(?:er|re)s?|l|lit(?:er|re)s?)\b",
    re.IGNORECASE,
)


def field_value(field: Any) -> str | None:
    if field is None:
        return None
    value = field.get("value") if isinstance(field, dict) else field.value
    return value if value is not None else None


def quality_flags(response: Any, lines: list[Any], raw_text: str) -> dict[str, Any]:
    solid_words, solid_mean_confidence = solid_word_stats(lines)
    line_confidences = [line.confidence for line in lines]
    average_confidence = sum(line_confidences) / len(line_confidences) if line_confidences else 0.0
    char_heights = [line.char_height_px for line in lines]
    dense_or_small = len(lines) >= 20 or (char_heights and min(char_heights) <= 12)
    poor = (
        response.quality.score < 0.35
        or not lines
        or solid_words < 3
        or average_confidence < 0.55
    )
    return {
        "ocr_confidence": round(average_confidence, 3),
        "solid_word_count": solid_words,
        "solid_word_mean_confidence": solid_mean_confidence,
        "line_char_height_min_px": min(char_heights) if char_heights else None,
        "line_char_height_median_px": round(sorted(char_heights)[len(char_heights) // 2], 2) if char_heights else None,
        "dense_or_small_text": dense_or_small,
        "poor_ocr_quality": poor,
        "contains_date_information": bool(DATE_RE.search(raw_text))
        or any(field_value(response.fields[name]) for name in ("manufacture_pack_import_date", "best_before_use_by")),
        "contains_mrp_information": bool(MRP_RE.search(raw_text)) or bool(field_value(response.fields["mrp"])),
        "contains_quantity_information": bool(QUANTITY_RE.search(raw_text)) or bool(field_value(response.fields["net_quantity"])),
    }


def evaluate_image(path: Path, pipeline: ExtractionPipeline) -> dict[str, Any]:
    captured: dict[str, Any] = {}
    original_run = pipeline.engine.run

    def capture(image: Any) -> Any:
        result = original_run(image)
        captured["result"] = result
        return result

    pipeline.engine.run = capture
    started = time.perf_counter()
    try:
        response = pipeline.run(path.read_bytes(), path.name)
        result = captured["result"]
        fields = {
            name: response.fields[name].model_dump(mode="json")
            for name in FIELDS
        }
        return {
            "status": "processed",
            "filename": path.name,
            "image_dimensions": {
                "width": response.image.width,
                "height": response.image.height,
            },
            "ocr_processing_time_ms": response.metadata.processing_time_ms if response.metadata else None,
            "batch_elapsed_time_ms": round((time.perf_counter() - started) * 1000, 2),
            "ocr_character_count": len(response.cleaned_ocr_text),
            "ocr_line_count": len(result.lines),
            **quality_flags(response, result.lines, response.raw_ocr_text),
            "fields": fields,
            "barcodes": {
                "status": "not_implemented_by_existing_system",
                "values": [],
            },
            "unmapped_ocr_text_detections": [
                detection.model_dump(mode="json") for detection in response.unmapped_detections
            ],
            "raw_ocr_text": response.raw_ocr_text,
            "cleaned_ocr_text": response.cleaned_ocr_text,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "filename": path.name,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "batch_elapsed_time_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    finally:
        pipeline.engine.run = original_run


def summarize(images: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [image for image in images if image["status"] == "processed"]
    failed = [image for image in images if image["status"] != "processed"]
    denominator = len(successful)

    field_frequency: dict[str, dict[str, Any]] = {}
    for field in FIELDS:
        count = sum(bool(field_value(image["fields"].get(field))) for image in successful)
        frequency = count / denominator if denominator else 0.0
        field_frequency[field] = {
            "detected_images": count,
            "frequency": round(frequency, 3),
            "missing_images": denominator - count,
            "missing_rate": round(1.0 - frequency, 3) if denominator else None,
        }

    processing_times = [image["ocr_processing_time_ms"] for image in successful if image["ocr_processing_time_ms"] is not None]
    confidences = [image["ocr_confidence"] for image in successful]
    return {
        "dataset_size": len(images),
        "images_processed_successfully": len(successful),
        "images_failed": len(failed),
        "average_processing_time_ms": round(sum(processing_times) / len(processing_times), 2) if processing_times else None,
        "average_ocr_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
        "field_extraction_frequency": field_frequency,
        "particularly_poor_ocr_quality": [image["filename"] for image in successful if image["poor_ocr_quality"]],
        "dense_or_small_text_images": [image["filename"] for image in successful if image["dense_or_small_text"]],
        "images_containing_barcodes": [],
        "images_containing_dates": [image["filename"] for image in successful if image["contains_date_information"]],
        "images_containing_mrp": [image["filename"] for image in successful if image["contains_mrp_information"]],
        "images_containing_quantity": [image["filename"] for image in successful if image["contains_quantity_information"]],
        "failed_images": [
            {key: image[key] for key in ("filename", "error_type", "error") if key in image}
            for image in failed
        ],
        "classification_notes": {
            "poor_ocr_quality": "quality score < 0.35, no OCR lines, fewer than 3 solid words, or mean line confidence < 0.55",
            "dense_or_small_text": "at least 20 OCR lines or minimum OCR line character height <= 12 px",
            "barcode": "No barcode detector exists in the existing Module 1 system; no barcode claims were made.",
            "information_presence": "Dates, MRP, and quantity are flagged from existing OCR text or corresponding extracted fields; this is not ground truth.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only batch evaluation using the existing Module 1 pipeline.")
    parser.add_argument("--image-dir", type=Path, default=Path("test_images/web"))
    parser.add_argument("--output", type=Path, default=Path("reports/web_batch_evaluation.json"))
    args = parser.parse_args()

    paths = sorted(path for path in args.image_dir.iterdir() if path.is_file())
    pipeline = ExtractionPipeline()
    images = [evaluate_image(path, pipeline) for path in paths]
    report = {
        "evaluation": "Stage 6E Web Product Image Batch Evaluation",
        "pipeline": "existing module1.services.pipeline.ExtractionPipeline",
        "ground_truth_used": False,
        "source_directory": str(args.image_dir),
        "summary": summarize(images),
        "images": images,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
