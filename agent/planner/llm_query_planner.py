from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

from agent.utils import canonical_db_name


class LLMQueryPlanner:
    """LLM-driven multi-DB query planner via OpenRouter Chat Completions.

    Inputs:
    - question: user query
    - available_databases: runtime-available DB engines
    - context: ContextBuilder output
    - few_shot_examples: top-k similar templates
    - prior_failures: recent failure categories

    Outputs:
    - plan dict or None on generation failure

    Assumptions:
    - OPENROUTER_API_KEY is provided via environment/.env.
    - MODEL_NAME selects model (overridable from CLI by setting env at runtime).
    """

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        self.repo_root = repo_root or Path(__file__).resolve().parents[2]
        load_dotenv(self.repo_root / ".env", override=False)
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip().rstrip("/")
        self.model = os.getenv("MODEL_NAME", "openai/gpt-4o-mini").strip() or "openai/gpt-4o-mini"
        self.site_url = os.getenv("OPENROUTER_SITE_URL", "").strip()
        self.app_name = os.getenv("OPENROUTER_APP_NAME", "OracleForge").strip()
        self.http = httpx.Client(timeout=45)

    def generate(
        self,
        question: str,
        available_databases: List[str],
        context: Dict[str, Any],
        few_shot_examples: List[Dict[str, Any]],
        prior_failures: Optional[List[str]] = None,
        priority_mode: str = "balanced",   # NEW
    complexity_score: float = 0.5      # NEW (0 simple → 1 complex)
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None

        available = [canonical_db_name(db) for db in available_databases if canonical_db_name(db)]
        schema_metadata = context.get("schema_metadata", {})
        join_hints = context.get("join_key_rules", [])[:20]
        failures = context.get("known_failures", [])[:8]
        resolved = context.get("resolved_patterns", [])[:8]

        prompt = {
            "task": "Generate executable SQL/Mongo queries for a multi-db analytics agent.",
            "question": question,
            "available_databases": available,
            "schema": schema_metadata,
            "join_hints": join_hints,
            "failure_patterns": failures,
            "resolved_patterns": resolved,
            "recent_failure_categories": prior_failures or [],
            "few_shot_examples": few_shot_examples,
            "constraints": [
                "Return strict JSON only.",
                "Use only available_databases.",
                "Mongo queries must be aggregation pipeline arrays.",
                "Prefer schema-valid table/collection/field names.",
                "Follow the structure of few_shot_examples unless clearly incorrect.",
                "Do not over-engineer simple aggregation queries (COUNT, SUM, MAX).",
                "Prefer single-table execution unless joins are explicitly needed.",
            ],
            # new prompt
            "execution_controls": {
                "priority_mode": priority_mode,
                "complexity_score": complexity_score,
                "rules": [
                    "If complexity_score < 0.3 → prefer single-table queries only",
                    "If priority_mode = 'accuracy' → avoid joins unless explicitly required",
                    "If priority_mode = 'complex' → allow multi-step aggregation and joins",
                    "Do NOT create multi-table aggregation for simple COUNT queries",
                ],
            },
            # end new prompt
            "output_schema": {
                "databases": ["postgresql", "mongodb"],
                "queries": {
                    "postgresql": "SELECT ...",
                    "mongodb": [{"$match": {}}, {"$group": {"_id": None, "count": {"$sum": 1}}}],
                },
                "join_plan": {
                    "left_key": "customer_id",
                    "right_key": "customer_id",
                    "strategy": "normalize",
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name

        body = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 700,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior query planner. Produce syntactically-correct SQL and Mongo pipelines "
                        "for the provided schema, with deterministic JSON output."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        }

        try:
            response = self.http.post(f"{self.base_url}/chat/completions", headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return None
            content = choices[0].get("message", {}).get("content", "{}")
            if isinstance(content, list):
                content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
            payload = json.loads(str(content).strip() or "{}")
            return self._normalize_payload(payload, available)
        except Exception:
            return None

    def _normalize_payload(self, payload: Dict[str, Any], available: List[str]) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None

        dbs = payload.get("databases", [])
        queries = payload.get("queries", {})
        join_plan = payload.get("join_plan", {})

        if not isinstance(dbs, list) or not isinstance(queries, dict):
            return None

        normalized_dbs: List[str] = []
        for db in dbs:
            name = canonical_db_name(str(db))
            if name and name in available and name not in normalized_dbs:
                normalized_dbs.append(name)

        if not normalized_dbs:
            return None

        normalized_queries: Dict[str, Any] = {}
        for db in normalized_dbs:
            value = queries.get(db)
            if db == "mongodb":
                if isinstance(value, list):
                    normalized_queries[db] = value
            else:
                if isinstance(value, str) and value.strip():
                    normalized_queries[db] = " ".join(value.split())

        if not normalized_queries:
            return None

        if not isinstance(join_plan, dict):
            join_plan = {}
        strategy = str(join_plan.get("strategy", "normalize")).lower().strip()
        if strategy not in {"cast", "normalize"}:
            strategy = "normalize"

        return {
            "databases": list(normalized_queries.keys()),
            "queries": normalized_queries,
            "join_plan": {
                "left_key": str(join_plan.get("left_key", "customer_id")),
                "right_key": str(join_plan.get("right_key", "customer_id")),
                "strategy": strategy,
            },
        }

