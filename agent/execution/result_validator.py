from __future__ import annotations

from typing import Any, Dict, List, Tuple


class ResultValidator:
    """Detect suspicious execution outcomes and request a bounded replan.

    Inputs:
    - question, generated plan, merged records, trace

    Outputs:
    - dict {should_replan, failure_type, reason}

    Assumptions:
    - Only lightweight checks; no heavy post-hoc reasoning.
    """

    def evaluate(
        self,
        question: str,
        plan: Dict[str, Any],
        records: List[Dict[str, Any]],
        trace: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        text = (question or "").lower()

        if any((entry.get("failure_type") == "join_key_mismatch") for entry in trace if isinstance(entry, dict)):
            return {
                "should_replan": True,
                "failure_type": "join_key_mismatch",
                "reason": "join_key_mismatch_observed",
            }

        expects_agg = any(token in text for token in ["count", "how many", "average", "avg", "max", "min", "sum", "total"])
        if expects_agg and not records:
            return {
                "should_replan": True,
                "failure_type": "schema_error",
                "reason": "empty_result_for_aggregation_query",
            }

        if ("count" in text or "how many" in text) and records:
            if not self._contains_count_like_value(records):
                return {
                    "should_replan": True,
                    "failure_type": "schema_error",
                    "reason": "missing_count_aggregation",
                }

        return {"should_replan": False, "failure_type": "", "reason": "ok"}

    @staticmethod
    def _contains_count_like_value(records: List[Dict[str, Any]]) -> bool:
        count_keys = {"count", "cnt", "total", "n", "biz_count"}
        for row in records:
            if not isinstance(row, dict):
                continue
            lowered = {str(k).lower(): v for k, v in row.items()}
            for key in count_keys:
                if key in lowered and isinstance(lowered[key], (int, float)):
                    return True
        return False

