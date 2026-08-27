"""
Runs every scenario in data/test_cases.json against the decision engine
and prints a pass/fail table — handy to show live during the demo.

Run with:
    python -m tests.test_rules
(from the SIH26034_Module2 folder, with the venv active)
"""

import json
from pathlib import Path
from app.models.schemas import ProductData
from app.services.decision_engine import run_compliance_check

TEST_CASES_PATH = Path(__file__).parent.parent / "data" / "test_cases.json"


def run_all_tests():
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"{'Test':45} {'Expected':22} {'Got':22} {'Result'}")
    print("-" * 100)

    passed = 0
    for case in cases:
        product = ProductData(**case["input"])
        result = run_compliance_check(product)
        ok = result.status == case["expected_status"]
        passed += ok
        print(f"{case['name']:45} {case['expected_status']:22} {result.status:22} {'PASS' if ok else 'FAIL'}")

    print("-" * 100)
    print(f"{passed}/{len(cases)} scenarios matched expected status.")


if __name__ == "__main__":
    run_all_tests()
