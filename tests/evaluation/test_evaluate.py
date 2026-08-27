from __future__ import annotations

from types import SimpleNamespace

from tests.evaluation.evaluate import compare_record, normalize, summarize


def test_normalization_handles_formatting_and_numeric_mrp_only():
    assert normalize("  Rs 50.00 ", "mrp") == "50"
    assert normalize("SnackWorks   Foods", "product_name") == "snackworks foods"
    assert normalize("50.00", "mrp") == normalize("50", "mrp")


def test_compare_record_distinguishes_exact_normalized_missing_incorrect_and_uncertain():
    fields = {
        "exact": SimpleNamespace(value="India", detection_status=SimpleNamespace(value="detected")),
        "mrp": SimpleNamespace(value="50", detection_status=SimpleNamespace(value="uncertain")),
        "wrong": SimpleNamespace(value="150", detection_status=SimpleNamespace(value="detected")),
    }
    result = compare_record({"exact": "India", "mrp": "50.00", "wrong": "120", "absent": "x"}, fields)
    assert result["exact"]["result"] == "exact_match"
    assert result["mrp"]["result"] == "normalized_match"
    assert result["mrp"]["uncertain"] is True
    assert result["wrong"]["result"] == "incorrect"
    assert result["absent"]["result"] == "missing"


def test_summarize_reports_field_metrics_and_ignores_unknown_fields():
    summary = summarize({
        "one.png": {
            "mrp": {"result": "exact_match", "uncertain": False},
            "net_quantity": {"result": "missing", "uncertain": False},
        }
    })
    assert summary["totals"]["expected"] == 2
    assert summary["totals"]["exact_match_accuracy"] == 0.5
    assert summary["per_field"]["mrp"]["precision"] == 1.0
    assert summary["per_field"]["net_quantity"]["recall"] == 0.0
