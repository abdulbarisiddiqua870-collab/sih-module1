from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from module1.services.pipeline import ExtractionPipeline


NUMERIC_FIELDS = {"mrp", "unit_sale_price"}
_PUNCTUATION = re.compile(r"[^a-z0-9@.+/%-]+")


def normalize(value: str, field: str | None = None) -> str:
    """Apply only formatting normalization, not semantic OCR correction."""
    text = " ".join(value.strip().lower().split())
    if field in NUMERIC_FIELDS:
        try:
            numeric = re.fullmatch(r"(?:rs\.?|inr|\$)?\s*([0-9]+(?:\.[0-9]+)?)", text)
            if numeric:
                return f"{float(numeric.group(1).replace(',', '')):g}"
        except ValueError:
            pass
    return _PUNCTUATION.sub(" ", text).strip()


def compare_field(expected: str, actual: str | None, field: str, uncertain: bool = False) -> dict[str, Any]:
    if actual is None:
        result = "missing"
    elif actual == expected:
        result = "exact_match"
    elif normalize(actual, field) == normalize(expected, field):
        result = "normalized_match"
    else:
        result = "incorrect"
    return {"expected": expected, "actual": actual, "result": result, "uncertain": uncertain}


def compare_record(expected: dict[str, str], fields: dict[str, Any]) -> dict[str, Any]:
    comparisons: dict[str, dict[str, Any]] = {}
    for field, expected_value in expected.items():
        extracted = fields.get(field)
        actual = getattr(extracted, "value", None) if extracted is not None else None
        status = getattr(getattr(extracted, "detection_status", None), "value", None)
        comparisons[field] = compare_field(expected_value, actual, field, status == "uncertain")
    return comparisons


def summarize(comparisons_by_image: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    per_field: dict[str, dict[str, int]] = {}
    totals = {"expected": 0, "exact_matches": 0, "normalized_matches": 0, "missing": 0, "incorrect": 0, "uncertain": 0}
    for comparisons in comparisons_by_image.values():
        for field, result in comparisons.items():
            stats = per_field.setdefault(field, {"expected": 0, "matches": 0, "exact_matches": 0, "missing": 0, "incorrect": 0, "uncertain": 0})
            stats["expected"] += 1
            totals["expected"] += 1
            if result["result"] == "exact_match":
                stats["matches"] += 1
                stats["exact_matches"] += 1
                totals["exact_matches"] += 1
            elif result["result"] == "normalized_match":
                stats["matches"] += 1
                totals["normalized_matches"] += 1
            elif result["result"] == "missing":
                stats["missing"] += 1
                totals["missing"] += 1
            else:
                stats["incorrect"] += 1
                totals["incorrect"] += 1
            if result["uncertain"]:
                stats["uncertain"] += 1
                totals["uncertain"] += 1
    for stats in per_field.values():
        denominator = stats["expected"]
        predicted = stats["matches"] + stats["incorrect"]
        relevant = stats["matches"] + stats["missing"] + stats["incorrect"]
        stats["precision"] = round(stats["matches"] / predicted, 3) if predicted else None
        stats["recall"] = round(stats["matches"] / relevant, 3) if relevant else None
        stats["exact_match_accuracy"] = round(stats["exact_matches"] / denominator, 3) if denominator else None
    denominator = totals["expected"]
    totals["normalized_match_accuracy"] = round((totals["exact_matches"] + totals["normalized_matches"]) / denominator, 3) if denominator else None
    totals["exact_match_accuracy"] = round(totals["exact_matches"] / denominator, 3) if denominator else None
    return {"totals": totals, "per_field": per_field}


def load_ground_truth(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    return payload["images"]


def run_evaluation(dataset_path: Path, image_dir: Path) -> dict[str, Any]:
    records = load_ground_truth(dataset_path)
    pipeline = ExtractionPipeline()
    comparisons: dict[str, dict[str, dict[str, Any]]] = {}
    images: list[dict[str, Any]] = []
    false_positives: list[dict[str, str]] = []
    for record in records:
        filename = record["filename"]
        response = pipeline.run((image_dir / filename).read_bytes(), filename)
        image_comparisons = compare_record(record.get("expected", {}), response.fields)
        for field in record.get("not_expected", []):
            extracted = response.fields.get(field)
            if extracted is not None and extracted.value is not None:
                false_positives.append({"filename": filename, "field": field, "actual": extracted.value})
        comparisons[filename] = image_comparisons
        images.append({
            "filename": filename,
            "condition": record.get("condition"),
            "available_fields": len(record.get("expected", {})),
            "comparisons": image_comparisons,
            "ocr_chars": len(response.cleaned_ocr_text),
            "processing_time_ms": response.metadata.processing_time_ms if response.metadata else None,
        })
    return {
        "dataset_size": len(records),
        "images": images,
        "metrics": summarize(comparisons),
        "false_positives": false_positives,
        "notes": "Omitted expected fields are unknown and are not scored as false positives.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the existing Module 1 pipeline against image ground truth.")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).with_name("ground_truth.json"))
    parser.add_argument("--image-dir", type=Path, default=Path("test_images"))
    args = parser.parse_args()
    print(json.dumps(run_evaluation(args.dataset, args.image_dir), indent=2))


if __name__ == "__main__":
    main()
