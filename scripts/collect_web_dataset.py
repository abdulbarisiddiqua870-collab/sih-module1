from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from module1.core.config import settings
from module1.services.pipeline import ExtractionPipeline
from module1.preprocessing.images import decode_image


DOWNLOAD_CHUNK = 64 * 1024
DEFAULT_TIMEOUT_SECONDS = 20
USABLE_QUALITY_THRESHOLD = 0.35
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_name(value: str, fallback: str) -> str:
    name = SAFE_NAME_RE.sub("_", Path(unquote(value)).name).strip("._")
    return name or fallback


def load_manifest(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    entries = payload.get("images", payload) if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError("Manifest must be a JSON list or an object with an 'images' list")
    result: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("url"), str):
            raise ValueError("Each manifest entry must contain a URL")
        normalized = dict(entry)
        normalized["category"] = str(entry.get("category") or "uncategorized")
        normalized["filename"] = str(entry.get("filename") or "")
        result.append(normalized)
    return result


def download_bytes(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported")
    request = Request(url, headers={"User-Agent": "sih-module1-dataset/1.0"})
    with urlopen(request, timeout=timeout) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > settings.max_upload_bytes:
            raise ValueError("download exceeds the configured upload limit")
        data = bytearray()
        while chunk := response.read(DOWNLOAD_CHUNK):
            if len(data) + len(chunk) > settings.max_upload_bytes:
                raise ValueError("download exceeds the configured upload limit")
            data.extend(chunk)
        return bytes(data)


def image_filename(entry: dict[str, Any], index: int) -> str:
    supplied = entry["filename"]
    if supplied:
        return safe_name(supplied, f"image-{index}.jpg")
    url_name = Path(unquote(urlparse(entry["url"]).path)).name
    return safe_name(url_name, f"image-{index}.jpg")


def unique_destination(output_dir: Path, relative_path: Path, digest: str) -> Path:
    destination = output_dir / relative_path
    if not destination.exists():
        return destination
    return destination.with_name(f"{destination.stem}-{digest[:8]}{destination.suffix}")


def image_dimensions_acceptable(width: int, height: int) -> bool:
    return min(width, height) >= settings.min_image_dimension


def confidence_summary(response) -> float | None:
    confidences = [field.confidence for field in response.fields.values() if field.value is not None]
    confidences.extend(detection.confidence for detection in response.unmapped_detections)
    return round(sum(confidences) / len(confidences), 3) if confidences else None


def inspect_image(data: bytes, filename: str, pipeline: ExtractionPipeline) -> dict[str, Any]:
    image = decode_image(data)
    if image is None:
        return {"status": "invalid_image", "filename": filename}
    started = time.perf_counter()
    response = pipeline.run(data, filename)
    height, width = image.shape[:2]
    detected = {
        name: {
            "value": field.value,
            "status": field.detection_status.value,
            "confidence": field.confidence,
        }
        for name, field in response.fields.items()
        if field.value is not None
    }
    return {
        "status": "processed",
        "filename": filename,
        "width": int(width),
        "height": int(height),
        "quality": response.quality.model_dump(),
        "ocr_characters": len(response.cleaned_ocr_text),
        "ocr_confidence": confidence_summary(response),
        "fields_detected": detected,
        "processing_time_ms": round((time.perf_counter() - started) * 1000, 2),
    }


def collect_entries(
    manifest: list[dict[str, Any]],
    output_dir: Path,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pipeline = ExtractionPipeline()
    hashes: dict[str, str] = {}
    metadata: list[dict[str, Any]] = []
    for index, entry in enumerate(manifest, start=1):
        item: dict[str, Any] = {
            "source": entry.get("source", "web"),
            "ground_truth": bool(entry.get("ground_truth", False)),
            "download_status": "pending",
            "duplicate_status": "not_checked",
            "source_url": entry["url"],
            "category": safe_name(entry["category"], "uncategorized"),
        }
        for key in ("search_query", "search_provider", "search_title", "source_page"):
            if entry.get(key):
                item[key] = entry[key]
        try:
            data = download_bytes(entry["url"], timeout)
            item["download_status"] = "downloaded"
            digest = hashlib.sha256(data).hexdigest()
            item["sha256"] = digest
            if digest in hashes:
                item.update({"status": "duplicate", "duplicate_status": "duplicate", "duplicate_of": hashes[digest]})
                metadata.append(item)
                continue
            filename = image_filename(entry, index)
            if Path(filename).suffix.lower() not in settings.allowed_extensions:
                item.update({"status": "unsupported_format", "duplicate_status": "unique", "filename": filename})
                metadata.append(item)
                continue
            image = decode_image(data)
            if image is None:
                item.update({"status": "invalid_image", "duplicate_status": "unique", "filename": filename})
                metadata.append(item)
                continue
            if not image_dimensions_acceptable(image.shape[1], image.shape[0]):
                item.update({"status": "too_small", "duplicate_status": "unique", "filename": filename})
                metadata.append(item)
                continue
            relative_path = Path(item["category"]) / filename
            destination = unique_destination(output_dir, relative_path, digest)
            relative_path = destination.relative_to(output_dir)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            hashes[digest] = str(relative_path)
            item["duplicate_status"] = "unique"
            item["path"] = str(relative_path)
            item.update(inspect_image(data, filename, pipeline))
        except Exception as exc:
            if item["download_status"] == "pending":
                item["download_status"] = "failed"
            item.update({"status": "download_or_processing_error", "error": str(exc)})
        metadata.append(item)

    report = make_report(metadata)
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def collect(manifest_path: Path, output_dir: Path, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    return collect_entries(load_manifest(manifest_path), output_dir, timeout)


def make_report(metadata: list[dict[str, Any]]) -> dict[str, Any]:
    processed = [item for item in metadata if item.get("status") == "processed"]
    usable = [
        item
        for item in processed
        if item.get("quality", {}).get("resolution_ok", False)
        and item.get("quality", {}).get("score", 0.0) >= USABLE_QUALITY_THRESHOLD
    ]
    fields: dict[str, int] = {}
    categories: dict[str, int] = {}
    for item in processed:
        category = item.get("category", "uncategorized")
        categories[category] = categories.get(category, 0) + 1
        for field in item.get("fields_detected", {}):
            fields[field] = fields.get(field, 0) + 1
    confidence_values = [item["ocr_confidence"] for item in processed if item.get("ocr_confidence") is not None]
    failed = sum(item.get("download_status") == "failed" for item in metadata)
    downloaded = sum(item.get("download_status") == "downloaded" for item in metadata)
    rejected = sum(item.get("status") in {"invalid_image", "unsupported_format", "too_small"} for item in metadata)
    processing_times = [item["processing_time_ms"] for item in processed]
    return {
        "total_candidates": len(metadata),
        "downloaded": downloaded,
        "images_processed": len(metadata),
        "usable_images": len(usable),
        "duplicates_removed": sum(item.get("status") == "duplicate" for item in metadata),
        "rejected": rejected,
        "failed": failed,
        "invalid_or_failed": sum(item.get("status") not in {"processed", "duplicate"} for item in metadata),
        "usable_quality_threshold": USABLE_QUALITY_THRESHOLD,
        "category_counts": categories,
        "resolution": [
            {"filename": item["filename"], "width": item["width"], "height": item["height"]}
            for item in processed
        ],
        "quality": [
            {"filename": item["filename"], **item["quality"]}
            for item in processed
        ],
        "ocr": [
            {"filename": item["filename"], "characters": item["ocr_characters"], "confidence": item["ocr_confidence"]}
            for item in processed
        ],
        "fields_detected": fields,
        "average_ocr_confidence": round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else None,
        "average_processing_time_ms": round(sum(processing_times) / len(processing_times), 2) if processing_times else None,
        "processing_time_ms": round(sum(processing_times), 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and OCR a categorized web-image dataset.")
    parser.add_argument("manifest", type=Path, help="JSON file containing image URLs and categories")
    parser.add_argument("--output-dir", type=Path, default=Path("web"))
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()
    report = collect(args.manifest, args.output_dir, args.timeout)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
