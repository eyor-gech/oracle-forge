from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Dict, List

from agent.dab_yelp_postgres import POSTGRES_SQL_BY_QUESTION


@dataclass
class TemplateMatch:
    question: str
    sql: str
    score: float


class TemplateRetriever:
    """Semantic retriever for SQL templates using lightweight cosine similarity.

    Inputs:
    - question: user natural-language query.
    - k: number of examples to return.

    Outputs:
    - list of top-k TemplateMatch ordered by similarity.

    Assumptions:
    - Existing SQL templates are authoritative and should remain unchanged.
    - Similarity is lexical/semantic-lite (token cosine) to keep runtime lightweight.
    """

    def __init__(self) -> None:
        self._templates = [
            {"question": q.strip(), "sql": " ".join(sql.split())}
            for q, sql in POSTGRES_SQL_BY_QUESTION.items()
        ]
        self._vectors = [self._vectorize(t["question"]) for t in self._templates]

    def retrieve(self, question: str, k: int = 4) -> List[TemplateMatch]:
        query_vec = self._vectorize(question)
        scored: List[TemplateMatch] = []
        for idx, template in enumerate(self._templates):
            score = self._cosine(query_vec, self._vectors[idx])
            scored.append(
                TemplateMatch(
                    question=template["question"],
                    sql=template["sql"],
                    score=round(score, 6),
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[: max(1, k)]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [tok for tok in re.findall(r"[a-z0-9_]+", (text or "").lower()) if tok]

    def _vectorize(self, text: str) -> Dict[str, float]:
        tokens = self._tokenize(text)
        vector: Dict[str, float] = {}
        for token in tokens:
            vector[token] = vector.get(token, 0.0) + 1.0
        norm = math.sqrt(sum(v * v for v in vector.values())) or 1.0
        for token in list(vector.keys()):
            vector[token] = vector[token] / norm
        return vector

    @staticmethod
    def _cosine(left: Dict[str, float], right: Dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        if len(left) > len(right):
            left, right = right, left
        return sum(value * right.get(key, 0.0) for key, value in left.items())

