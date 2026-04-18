from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List, Tuple


class PlanValidator:
    """Validate and lightly auto-fix LLM-generated plans.

    Inputs:
    - plan: {databases, queries, join_plan}
    - schema_metadata: introspected schema map

    Outputs:
    - {valid, plan, failure_type, issues}

    Assumptions:
    - Lightweight syntax/structure checks only.
    - Fixes only obvious issues; otherwise marks plan invalid.
    """

    STAGE_ORDER = {"$match": 1, "$group": 2, "$project": 3, "$sort": 4, "$limit": 5}

    def validate(self, plan: Dict[str, Any], schema_metadata: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(plan, dict):
            return {"valid": False, "plan": {}, "failure_type": "schema_error", "issues": ["plan_not_dict"]}

        working = deepcopy(plan)
        issues: List[str] = []
        failure_type = ""

        databases = working.get("databases", [])
        queries = working.get("queries", {})
        if not isinstance(databases, list) or not isinstance(queries, dict):
            return {"valid": False, "plan": working, "failure_type": "schema_error", "issues": ["missing_databases_or_queries"]}

        fixed_queries: Dict[str, Any] = {}
        for db in databases:
            query = queries.get(db)
            schema = schema_metadata.get(db, {}) if isinstance(schema_metadata, dict) else {}
            if db == "mongodb":
                valid, fixed, db_issues = self._validate_mongo_pipeline(query, schema)
            else:
                valid, fixed, db_issues = self._validate_sql_query(str(db), query, schema)
            issues.extend(db_issues)
            if not valid:
                failure_type = "schema_error"
                return {"valid": False, "plan": working, "failure_type": failure_type, "issues": issues}
            fixed_queries[db] = fixed

        working["queries"] = fixed_queries

        join_valid, join_issues = self._validate_join_plan(working, schema_metadata)
        issues.extend(join_issues)
        if not join_valid:
            return {"valid": False, "plan": working, "failure_type": "join_key_mismatch", "issues": issues}

        return {"valid": True, "plan": working, "failure_type": "", "issues": issues}

    def _validate_sql_query(self, db: str, query: Any, schema: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
        issues: List[str] = []
        if not isinstance(query, str) or not query.strip():
            return False, "", [f"{db}:empty_sql"]
        sql = " ".join(query.split())

        tables = self._schema_tables(schema)
        table_cols = self._table_columns(schema)

        table_refs = self._extract_table_refs(sql)
        if table_refs and tables:
            for table in table_refs:
                if table not in tables:
                    return False, sql, [f"{db}:unknown_table:{table}"]

        select_exprs = self._extract_select_expressions(sql)
        if not select_exprs:
            return True, sql, issues

        if any(expr.strip() == "*" for expr in select_exprs):
            return True, sql, issues

        valid_exprs: List[str] = []
        all_columns = set(col for cols in table_cols.values() for col in cols)

        for expr in select_exprs:
            stripped = expr.strip()
            if "(" in stripped and ")" in stripped:
                valid_exprs.append(stripped)
                continue
            candidate = stripped.split()[-1]
            candidate = candidate.split(".")[-1]
            candidate = candidate.strip('"`[]')
            if not all_columns or candidate in all_columns:
                valid_exprs.append(stripped)
            else:
                issues.append(f"{db}:removed_invalid_column:{candidate}")

        if not valid_exprs:
            return False, sql, issues + [f"{db}:all_select_columns_invalid"]

        fixed_sql = self._replace_select_clause(sql, valid_exprs)
        return True, fixed_sql, issues

    def _validate_mongo_pipeline(self, pipeline: Any, schema: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
        issues: List[str] = []
        if not isinstance(pipeline, list):
            return False, [], ["mongodb:pipeline_not_list"]

        valid_fields = self._schema_fields(schema)
        cleaned: List[Dict[str, Any]] = []

        for stage in pipeline:
            if not isinstance(stage, dict) or len(stage) != 1:
                issues.append("mongodb:invalid_stage_shape")
                continue
            op, body = next(iter(stage.items()))
            if op not in self.STAGE_ORDER:
                issues.append(f"mongodb:unsupported_stage:{op}")
                continue

            if op in {"$match", "$project", "$sort"} and isinstance(body, dict):
                filtered = {k: v for k, v in body.items() if self._mongo_field_ok(k, valid_fields)}
                if len(filtered) != len(body):
                    issues.append(f"mongodb:removed_invalid_fields:{op}")
                body = filtered

            if op == "$group" and isinstance(body, dict):
                if "_id" not in body:
                    body["_id"] = None
                    issues.append("mongodb:group_missing_id_fixed")
                group_fixed: Dict[str, Any] = {"_id": body.get("_id")}
                for key, val in body.items():
                    if key == "_id":
                        continue
                    if isinstance(val, dict):
                        refs = [v for v in val.values() if isinstance(v, str) and v.startswith("$")]
                        if not refs or all(self._mongo_field_ok(ref[1:], valid_fields) for ref in refs):
                            group_fixed[key] = val
                        else:
                            issues.append(f"mongodb:removed_invalid_group_field:{key}")
                body = group_fixed

            cleaned.append({op: body})

        if not cleaned:
            return False, [], issues + ["mongodb:empty_pipeline_after_validation"]

        cleaned.sort(key=lambda item: self.STAGE_ORDER.get(next(iter(item.keys())), 99))
        return True, cleaned, issues

    def _validate_join_plan(self, plan: Dict[str, Any], schema_metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        issues: List[str] = []
        join_plan = plan.get("join_plan", {})
        databases = plan.get("databases", [])
        if not isinstance(join_plan, dict) or not isinstance(databases, list) or len(databases) < 2:
            return True, issues

        left_key = str(join_plan.get("left_key", "")).strip()
        right_key = str(join_plan.get("right_key", "")).strip()
        if not left_key or not right_key:
            return False, ["join:missing_join_keys"]

        left_db = str(databases[0])
        right_db = str(databases[1])

        left_fields = self._schema_fields(schema_metadata.get(left_db, {}))
        right_fields = self._schema_fields(schema_metadata.get(right_db, {}))

        if left_fields and left_key not in left_fields:
            return False, [f"join:left_key_missing:{left_db}.{left_key}"]
        if right_fields and right_key not in right_fields:
            return False, [f"join:right_key_missing:{right_db}.{right_key}"]

        return True, issues

    @staticmethod
    def _schema_tables(schema: Dict[str, Any]) -> List[str]:
        out: List[str] = []
        for key in ["tables", "collections"]:
            items = schema.get(key, []) if isinstance(schema, dict) else []
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, str):
                    out.append(item)
                elif isinstance(item, dict) and isinstance(item.get("name"), str):
                    out.append(item["name"])
        return out

    @staticmethod
    def _schema_fields(schema: Dict[str, Any]) -> set[str]:
        fields: set[str] = set()
        for key in ["tables", "collections"]:
            items = schema.get(key, []) if isinstance(schema, dict) else []
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    raw = item.get("fields", {})
                    if isinstance(raw, dict):
                        fields.update(str(k) for k in raw.keys())
        return fields

    @staticmethod
    def _schema_table_columns(schema: Dict[str, Any]) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for key in ["tables", "collections"]:
            items = schema.get(key, []) if isinstance(schema, dict) else []
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    cols: List[str] = []
                    fields = item.get("fields", {})
                    if isinstance(fields, dict):
                        cols = [str(k) for k in fields.keys()]
                    out[item["name"]] = cols
        return out

    def _table_columns(self, schema: Dict[str, Any]) -> Dict[str, List[str]]:
        return self._schema_table_columns(schema)

    @staticmethod
    def _extract_table_refs(sql: str) -> List[str]:
        refs = re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", sql, flags=re.IGNORECASE)
        cleaned: List[str] = []
        for ref in refs:
            value = ref.split(".")[-1].strip('"`[]')
            if value and value not in cleaned:
                cleaned.append(value)
        return cleaned

    @staticmethod
    def _extract_select_expressions(sql: str) -> List[str]:
        match = re.search(r"\bselect\b\s+(.*?)\s+\bfrom\b", sql, flags=re.IGNORECASE)
        if not match:
            return []
        clause = match.group(1).strip()
        if not clause:
            return []
        return [part.strip() for part in clause.split(",") if part.strip()]

    @staticmethod
    def _replace_select_clause(sql: str, select_exprs: List[str]) -> str:
        if not select_exprs:
            return sql
        return re.sub(
            r"(\bselect\b\s+)(.*?)(\s+\bfrom\b)",
            lambda m: f"{m.group(1)}{', '.join(select_exprs)}{m.group(3)}",
            sql,
            count=1,
            flags=re.IGNORECASE,
        )

    @staticmethod
    def _mongo_field_ok(field: str, valid_fields: set[str]) -> bool:
        if not field:
            return False
        if field.startswith("$"):
            field = field[1:]
        root = field.split(".", 1)[0]
        if not valid_fields:
            return True
        return root in valid_fields

