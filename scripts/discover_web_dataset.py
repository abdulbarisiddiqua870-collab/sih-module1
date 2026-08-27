from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.collect_web_dataset import collect_entries, safe_name


DEFAULT_CATEGORIES = (
    "biscuits",
    "chips",
    "namkeen",
    "noodles",
    "chocolates",
    "beverages",
    "spices",
    "packaged snacks",
    "personal care",
    "household products",
)
QUERY_SUFFIX = " product packaging label back pack MRP ingredients net quantity"
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        ...


class SerpApiImageProvider:
    """Optional provider adapter for SerpApi's Google Images endpoint."""

    name = "serpapi-google-images"

    def __init__(self, api_key: str, timeout: int = 20) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str, limit: int) -> list[dict[str, Any]]:
        params = urlencode({"engine": "google_images", "q": query, "api_key": self.api_key, "ijn": "0"})
        request = Request(
            f"https://serpapi.com/search.json?{params}",
            headers={"User-Agent": "sih-module1-discovery/1.0"},
        )
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read())
        results: list[dict[str, Any]] = []
        for result in payload.get("images_results", [])[:limit]:
            url = result.get("original")
            if isinstance(url, str):
                results.append({
                    "url": url,
                    "title": result.get("title", ""),
                    "source_page": result.get("link", ""),
                })
        return results


def build_queries(categories: list[str]) -> list[tuple[str, str]]:
    return [(category, f"{category}{QUERY_SUFFIX}") for category in categories]


def is_candidate(result: dict[str, Any]) -> bool:
    url = result.get("url")
    if not isinstance(url, str) or urlparse(url).scheme not in {"http", "https"}:
        return False
    suffix = Path(urlparse(url).path).suffix.lower()
    return not suffix or suffix in SUPPORTED_SUFFIXES


def discover_candidates(
    categories: list[str],
    provider: SearchProvider,
    max_images: int = 100,
    results_per_category: int = 20,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for category, query in build_queries(categories):
        if len(candidates) >= max_images:
            break
        try:
            results = provider.search(query, results_per_category)
        except Exception:
            continue
        for result in results:
            url = result.get("url")
            if not is_candidate(result) or url in seen_urls:
                continue
            seen_urls.add(url)
            url_name = Path(urlparse(url).path).name
            suffix = Path(urlparse(url).path).suffix.lower()
            filename = url_name if suffix in SUPPORTED_SUFFIXES else f"candidate-{len(candidates) + 1}.jpg"
            candidates.append({
                "url": url,
                "category": category,
                "filename": filename,
                "search_query": query,
                "search_provider": provider.name,
                "source": "web",
                "ground_truth": False,
                "search_title": result.get("title", ""),
                "source_page": result.get("source_page", ""),
            })
            if len(candidates) >= max_images:
                break
    return candidates


def load_categories(path: Path | None, values: list[str]) -> list[str]:
    if path is not None:
        payload = json.loads(path.read_text())
        categories = payload.get("categories", payload) if isinstance(payload, dict) else payload
        if not isinstance(categories, list):
            raise ValueError("Category configuration must be a JSON list or an object with 'categories'")
        return [str(value) for value in categories if str(value).strip()]
    return values or list(DEFAULT_CATEGORIES)


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover categorized product-package image URLs and optionally collect them.")
    parser.add_argument("categories", nargs="*", help="categories to search; defaults to the standard product categories")
    parser.add_argument("--categories-file", type=Path, help="JSON list or object containing a categories list")
    parser.add_argument("--provider", choices=("serpapi",), default="serpapi")
    parser.add_argument("--max-images", type=int, default=100)
    parser.add_argument("--results-per-category", type=int, default=20)
    parser.add_argument("--output-dir", type=Path, default=Path("web"))
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true", help="discover and print candidates without downloading")
    args = parser.parse_args()
    categories = load_categories(args.categories_file, args.categories)
    if args.max_images <= 0 or args.results_per_category <= 0:
        parser.error("--max-images and --results-per-category must be positive")
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        payload = {
            "status": "not_configured",
            "message": "No discovery provider credentials configured; set SERPAPI_API_KEY to use the optional SerpApi adapter.",
            "provider": "serpapi",
            "categories": [safe_name(category, "uncategorized") for category in categories],
            "max_images": args.max_images,
            "dry_run": args.dry_run,
        }
        print(json.dumps(payload, indent=2))
        raise SystemExit(2)

    provider = SerpApiImageProvider(api_key, args.timeout)
    candidates = discover_candidates(categories, provider, args.max_images, args.results_per_category)
    if args.dry_run:
        print(json.dumps({"provider": provider.name, "candidates": candidates}, indent=2))
        return
    report = collect_entries(candidates, args.output_dir, args.timeout)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
