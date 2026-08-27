from __future__ import annotations

import json

from scripts.collect_web_dataset import image_dimensions_acceptable, load_manifest, make_report, safe_name, unique_destination


def test_safe_name_prevents_nested_paths():
    assert safe_name("../../biscuits", "fallback") == "biscuits"
    assert safe_name("", "fallback") == "fallback"


def test_load_manifest_accepts_list_and_images_object(tmp_path):
    list_path = tmp_path / "list.json"
    list_path.write_text(json.dumps([{"url": "https://example.test/a.jpg", "category": "biscuits"}]))
    object_path = tmp_path / "object.json"
    object_path.write_text(json.dumps({"images": [{"url": "https://example.test/b.jpg"}]}))
    assert load_manifest(list_path)[0]["category"] == "biscuits"
    assert load_manifest(object_path)[0]["category"] == "uncategorized"


def test_report_counts_processed_and_duplicates():
    report = make_report([
        {"status": "processed", "download_status": "downloaded", "filename": "a.jpg", "width": 100, "height": 200, "quality": {"resolution_ok": True, "score": 0.8}, "ocr_characters": 10, "ocr_confidence": 0.8, "fields_detected": {"mrp": {}}, "processing_time_ms": 12},
        {"status": "duplicate", "download_status": "downloaded"},
        {"status": "unsupported_format"},
    ])
    assert report["images_processed"] == 3
    assert report["usable_images"] == 1
    assert report["duplicates_removed"] == 1
    assert report["fields_detected"] == {"mrp": 1}
    assert report["total_candidates"] == 3
    assert report["downloaded"] == 2
    assert report["average_ocr_confidence"] == 0.8


def test_unique_destination_avoids_overwriting_existing_file(tmp_path):
    relative = tmp_path / "biscuits" / "label.jpg"
    relative.parent.mkdir()
    relative.write_bytes(b"existing")
    destination = unique_destination(tmp_path, relative.relative_to(tmp_path), "abcdef123456")
    assert destination.name == "label-abcdef12.jpg"


def test_extremely_small_images_are_not_acceptable():
    assert image_dimensions_acceptable(100, 200)
    assert not image_dimensions_acceptable(99, 200)
