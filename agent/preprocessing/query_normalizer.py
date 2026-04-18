from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueryNormalizer:
    """Lightweight query normalizer for routing/template retrieval.

    Inputs:
    - raw query string

    Outputs:
    - normalized string with stable replacements

    Assumptions:
    - Only used for routing/template retrieval (not final user-visible query text).
    """

    def normalize(self, text: str) -> str:
        value = (text or "").strip().lower()
        replacements = {
            "how many": "count",
            "highest": "max",
        }
        for src, dst in replacements.items():
            value = value.replace(src, dst)
        return " ".join(value.split())

