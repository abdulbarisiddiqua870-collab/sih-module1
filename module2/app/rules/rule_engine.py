"""
Loads machine-readable rules from rules.json.

Keeping rules OUT of Python code is the core design decision of Module 2:
when regulations change, we edit JSON, not the application.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

RULES_PATH = Path(__file__).parent / "rules.json"


class RuleEngine:
    def __init__(self, rules_path: Path = RULES_PATH):
        with open(rules_path, "r", encoding="utf-8") as f:
            self._rules_by_category = json.load(f)

    def get_rules(self, category: str) -> List[Dict[str, Any]]:
        category_block = self._rules_by_category.get(category)
        if not category_block:
            # Fall back to packaged_food if an unknown category is sent
            category_block = self._rules_by_category.get("packaged_food", {})
        return category_block.get("rules", [])

    def get_version_info(self, category: str) -> Dict[str, str]:
        block = self._rules_by_category.get(category, {})
        return {
            "rule_source": block.get("rule_source", "unknown"),
            "version": block.get("version", "unknown"),
        }


rule_engine = RuleEngine()
