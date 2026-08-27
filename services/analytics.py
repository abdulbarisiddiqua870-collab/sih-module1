"""
Analytics over stored, normalized inspection records.

Module 3 never invents or recalculates a compliance decision here -
this module only aggregates and counts what Module 2 already decided,
for the dashboard and analytics pages.
"""

from collections import Counter

from config import STATUS_PASS, STATUS_REVIEW, STATUS_HIGH_PRIORITY


def compute_dashboard_stats(records: list) -> dict:
    total = len(records)
    status_counts = Counter(r["assessment"].get("status") for r in records)
    scores = [r["assessment"]["score"] for r in records if r["assessment"].get("score") is not None]

    return {
        "total": total,
        "pass_count": status_counts.get(STATUS_PASS, 0),
        "review_count": status_counts.get(STATUS_REVIEW, 0),
        "high_priority_count": status_counts.get(STATUS_HIGH_PRIORITY, 0),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "status_counts": dict(status_counts),
    }


def compute_score_distribution(records: list) -> list:
    return [r["assessment"]["score"] for r in records if r["assessment"].get("score") is not None]


def compute_violation_categories(records: list, top_n: int = 8) -> dict:
    types = Counter()
    for r in records:
        for f in r.get("findings", []):
            types[f.get("type", "UNKNOWN")] += 1
    return dict(types.most_common(top_n))


def compute_trend(records: list) -> list:
    """Return [(timestamp, score), ...] sorted chronologically."""
    rows = [
        (r["timestamp"], r["assessment"]["score"])
        for r in records
        if r["assessment"].get("score") is not None
    ]
    rows.sort(key=lambda x: x[0])
    return rows


def compute_full_analytics(records: list) -> dict:
    total = len(records)
    stats = compute_dashboard_stats(records)

    def pct(n):
        return round(100 * n / total, 1) if total else 0.0

    return {
        **stats,
        "pass_pct": pct(stats["pass_count"]),
        "review_pct": pct(stats["review_count"]),
        "high_priority_pct": pct(stats["high_priority_count"]),
        "score_distribution": compute_score_distribution(records),
        "violation_categories": compute_violation_categories(records),
        "trend": compute_trend(records),
    }
