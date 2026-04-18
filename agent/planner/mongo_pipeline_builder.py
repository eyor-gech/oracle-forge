from __future__ import annotations

from typing import Any, Dict, List


class MongoPipelineBuilder:
    """Build and validate MongoDB aggregation pipelines.

    Inputs:
    - question: NL question.
    - collection_schema: introspected schema dict for collection.
    - llm_pipeline: optional LLM-generated stages.

    Outputs:
    - safe aggregation pipeline list containing supported stages.

    Assumptions:
    - Pipeline must use known schema fields whenever possible.
    - Unsupported/invalid stages are dropped to keep execution safe.
    """

    SUPPORTED_STAGES = {"$match", "$group", "$project", "$sort", "$limit"}
    STAGE_ORDER = {"$match": 1, "$group": 2, "$project": 3, "$sort": 4, "$limit": 5}

    def build_pipeline(
        self,
        question: str,
        collection_schema: Dict[str, Any],
        llm_pipeline: Any = None,
    ) -> List[Dict[str, Any]]:
        valid_fields = set((collection_schema or {}).get("fields", {}).keys())
        if llm_pipeline:
            validated = self._validate_pipeline(llm_pipeline, valid_fields)
            if validated:
                return validated
        return self._intent_pipeline(question, valid_fields)

    def _validate_pipeline(self, pipeline: Any, valid_fields: set[str]) -> List[Dict[str, Any]]:
        if not isinstance(pipeline, list):
            return []
        cleaned: List[Dict[str, Any]] = []
        for stage in pipeline:
            if not isinstance(stage, dict) or len(stage) != 1:
                continue
            op = next(iter(stage.keys()))
            if op not in self.SUPPORTED_STAGES:
                continue
            body = stage.get(op)
            if op in {"$match", "$project", "$sort"} and isinstance(body, dict):
                body = {k: v for k, v in body.items() if self._field_ok(k, valid_fields)}
            if op == "$group" and isinstance(body, dict):
                if "_id" not in body:
                    body["_id"] = None
                group_body: Dict[str, Any] = {}
                for key, value in body.items():
                    if key == "_id":
                        group_body[key] = value
                        continue
                    if isinstance(value, dict):
                        field_ref = next((v for v in value.values() if isinstance(v, str) and v.startswith("$")), "")
                        field_name = field_ref[1:] if field_ref else ""
                        if not field_name or self._field_ok(field_name, valid_fields):
                            group_body[key] = value
                body = group_body
            if op == "$limit":
                try:
                    body = int(body)
                except Exception:
                    body = 100
                body = max(1, min(1000, body))
            cleaned.append({op: body})
        cleaned.sort(key=lambda stage: self.STAGE_ORDER.get(next(iter(stage.keys())), 99))
        return cleaned

    def _intent_pipeline(self, question: str, valid_fields: set[str]) -> List[Dict[str, Any]]:
        text = (question or "").lower()
        pipeline: List[Dict[str, Any]] = []

        if "2018" in text and self._field_ok("date", valid_fields):
            pipeline.append({"$match": {"date": {"$regex": "2018", "$options": "i"}}})

        if ("negative" in text or "sentiment" in text) and self._field_ok("text", valid_fields):
            pipeline.append(
                {
                    "$match": {
                        "text": {
                            "$regex": "frustrated|angry|terrible|awful|worst|broken|complaint|unhappy",
                            "$options": "i",
                        }
                    }
                }
            )

        if ("average" in text or "avg" in text) and self._field_ok("rating", valid_fields):
            pipeline.append({"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}})
            pipeline.append({"$project": {"_id": 0, "avg_rating": 1}})
            pipeline.sort(key=lambda stage: self.STAGE_ORDER.get(next(iter(stage.keys())), 99))
            return pipeline

        if "count" in text or "how many" in text:
            pipeline.append({"$group": {"_id": None, "count": {"$sum": 1}}})
            pipeline.append({"$project": {"_id": 0, "count": 1}})
            pipeline.sort(key=lambda stage: self.STAGE_ORDER.get(next(iter(stage.keys())), 99))
            return pipeline

        if self._field_ok("rating", valid_fields):
            pipeline.append({"$project": {"rating": 1, "text": 1, "business_id": 1}})
            pipeline.append({"$sort": {"rating": -1}})

        pipeline.append({"$limit": 100})
        pipeline.sort(key=lambda stage: self.STAGE_ORDER.get(next(iter(stage.keys())), 99))
        return pipeline

    @staticmethod
    def _field_ok(field: str, valid_fields: set[str]) -> bool:
        if not field:
            return False
        if field.startswith("$"):
            field = field[1:]
        if not valid_fields:
            return True
        root = field.split(".", 1)[0]
        return root in valid_fields

