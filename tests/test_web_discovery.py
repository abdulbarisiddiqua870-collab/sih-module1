from __future__ import annotations

from scripts.discover_web_dataset import build_queries, discover_candidates, is_candidate, load_categories


class FakeProvider:
    name = "fake"

    def search(self, query, limit):
        return [
            {"url": "https://cdn.example/label-one.jpg", "title": "front product package"},
            {"url": "https://cdn.example/label-one.jpg", "title": "duplicate"},
            {"url": "https://cdn.example/label-two.webp", "title": "package"},
            {"url": "https://cdn.example/label-three", "title": "back label"},
        ][:limit]


def test_build_queries_adds_label_focused_terms():
    assert build_queries(["biscuits"])[0][1].endswith("product packaging label back pack MRP ingredients net quantity")


def test_discovery_filters_unsupported_and_duplicate_urls():
    results = discover_candidates(["biscuits"], FakeProvider(), max_images=10, results_per_category=10)
    assert [result["url"] for result in results] == [
        "https://cdn.example/label-one.jpg",
        "https://cdn.example/label-three",
    ]
    assert all(result["source"] == "web" and result["ground_truth"] is False for result in results)


def test_is_candidate_rejects_non_http_and_unsupported_suffixes():
    assert is_candidate({"url": "https://example.test/a.png"})
    assert not is_candidate({"url": "https://example.test/a.webp"})
    assert not is_candidate({"url": "file:///tmp/a.jpg"})


def test_load_categories_from_file(tmp_path):
    path = tmp_path / "categories.json"
    path.write_text('{"categories": ["biscuits", "spices"]}')
    assert load_categories(path, []) == ["biscuits", "spices"]
