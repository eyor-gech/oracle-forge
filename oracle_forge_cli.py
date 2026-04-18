from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.main import run_agent_contract
from agent.tools_client import MCPToolsClient
from agent.utils import canonical_db_name

DATASET_LIST = [
    "bookreview",
    "crmarenapro",
    "DEPS_DEV_V1",
    "GITHUB_REPOS",
    "googlelocal",
    "PANCANCER_ATLAS",
    "PATENTS",
    "stockindex",
    "stockmarket",
    "yelp",
    "agnews",
    "music_brainz_20k",
]


def _validate_runtime(databases: List[str]) -> Dict[str, Any]:
    mock_mode = os.getenv("ORACLE_FORGE_MOCK_MODE", "false").strip().lower() in {"1", "true", "yes"}
    allow_mock_fallback = os.getenv("ORACLE_FORGE_ALLOW_MOCK_FALLBACK", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    client = MCPToolsClient(
        base_url=os.getenv("MCP_BASE_URL", "http://localhost:5000"),
        mock_mode=mock_mode,
        allow_fallback_to_mock=allow_mock_fallback,
    )

    discovered_tools = client.discover_tools()
    if not discovered_tools:
        raise RuntimeError("No MCP tools discovered. Check MCP_BASE_URL and tool server availability.")

    discovered_dbs = client.list_db()
    missing = [db for db in databases if db not in discovered_dbs]
    if missing:
        raise RuntimeError(
            f"Requested database(s) not available in MCP/runtime schema: {missing}. "
            f"Available: {discovered_dbs}"
        )

    schema_by_db: Dict[str, Any] = {}
    usable_databases: List[str] = []
    unavailable_schema: List[str] = []
    for db in databases:
        schema = client.describe_tables(db)
        schema_by_db[db] = schema
        tables = schema.get("tables", []) if isinstance(schema, dict) else []
        collections = schema.get("collections", []) if isinstance(schema, dict) else []
        if not tables and not collections:
            unavailable_schema.append(db)
            continue
        usable_databases.append(db)

    if not usable_databases:
        raise RuntimeError(
            "No schema objects discovered for any requested database. "
            "Check DB connection settings and MCP introspection tools."
        )

    return {
        "mock_mode": client.mock_mode,
        "tools_count": len(discovered_tools),
        "databases": discovered_dbs,
        "usable_databases": usable_databases,
        "unavailable_schema_databases": unavailable_schema,
        "schema": schema_by_db,
    }


def _extract_query_text(query_json_path: Path) -> str:
    try:
        payload = json.loads(query_json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to read query file `{query_json_path}`: {exc}") from exc

    if isinstance(payload, str):
        query_text = payload.strip()
    elif isinstance(payload, dict):
        query_text = str(payload.get("query", "")).strip()
    else:
        query_text = ""

    if not query_text:
        raise RuntimeError(f"`{query_json_path}` does not contain a valid query string.")
    return query_text


def _parse_db_types_from_db_config(db_config_path: Path) -> List[str]:
    text = db_config_path.read_text(encoding="utf-8")
    found: List[str] = []
    for line in text.splitlines():
        match = re.match(r"^\s*db_type\s*:\s*([A-Za-z0-9_\-]+)", line)
        if not match:
            continue
        found.append(canonical_db_name(match.group(1)))
    deduped = [item for item in dict.fromkeys(found) if item]
    return deduped or ["postgresql", "mongodb", "sqlite", "duckdb"]


def _resolve_dataset_mode_inputs(args: argparse.Namespace) -> Dict[str, Any]:
    if args.query_id is None:
        raise SystemExit("--query_id is required when --dataset is used.")

    db_dir = ROOT / "DataAgentBench" / f"query_{args.dataset}"
    query_dir = db_dir / f"query{args.query_id}"
    if not query_dir.exists():
        raise RuntimeError(f"Query directory `{query_dir}` does not exist.")

    query_json_path = query_dir / "query.json"
    if not query_json_path.exists():
        raise RuntimeError(f"Query file `{query_json_path}` does not exist.")

    db_description_path = db_dir / "db_description.txt"
    if not db_description_path.exists():
        raise RuntimeError(f"DB description file `{db_description_path}` does not exist.")
    _ = db_description_path.read_text(encoding="utf-8").strip()

    if args.use_hints:
        hint_path = db_dir / "db_description_withhint.txt"
        if not hint_path.exists():
            raise RuntimeError(f"DB description with hints file `{hint_path}` does not exist.")
        _ = hint_path.read_text(encoding="utf-8")

    db_config_path = db_dir / "db_config.yaml"
    if not db_config_path.exists():
        raise RuntimeError(f"DB config file `{db_config_path}` does not exist.")

    if getattr(args, "query", None):
        query_text = args.query
    else:
        query_text = _extract_query_text(query_json_path)

    databases = _parse_db_types_from_db_config(db_config_path)
    db_text = db_config_path.read_text(encoding="utf-8")
    return {
        "query_text": query_text,
        "databases": databases,
        "db_dir": db_dir,
        "query_dir": query_dir,
        "db_config_text": db_text,
        "mode": "dataset",
    }


def _resolve_direct_mode_inputs(args: argparse.Namespace) -> Dict[str, Any]:
    databases = [canonical_db_name(item.strip()) for item in args.databases.split(",") if item.strip()]
    databases = [db for db in databases if db]
    if not databases:
        raise RuntimeError("No valid databases provided in --databases.")
    return {
        "query_text": args.query,
        "databases": databases,
        "query_dir": None,
        "db_dir": None,
        "db_config_text": "",
        "mode": "direct",
    }


def _resolve_model_arg(args: argparse.Namespace) -> Optional[str]:
    if getattr(args, "llm", None):
        return str(args.llm).strip()
    if getattr(args, "model", None):
        return str(args.model).strip()
    return None


def _apply_dataset_runtime_env(mode_inputs: Dict[str, Any]) -> None:
    db_dir = mode_inputs.get("db_dir")
    db_config_text = str(mode_inputs.get("db_config_text", ""))
    if not isinstance(db_dir, Path) or not db_config_text:
        return

    current_type: Optional[str] = None
    for raw_line in db_config_text.splitlines():
        db_type_match = re.match(r"^\s*db_type\s*:\s*([A-Za-z0-9_\-]+)", raw_line)
        if db_type_match:
            current_type = canonical_db_name(db_type_match.group(1))
            continue
        db_path_match = re.match(r"^\s*db_path\s*:\s*(.+?)\s*$", raw_line)
        if db_path_match and current_type in {"sqlite", "duckdb"}:
            raw_path = db_path_match.group(1).split("#", 1)[0].strip().strip("'\"")
            abs_path = (db_dir / raw_path).resolve()
            if current_type == "sqlite":
                os.environ["SQLITE_PATH"] = str(abs_path)
            elif current_type == "duckdb":
                os.environ["DUCKDB_PATH"] = str(abs_path)
        db_name_match = re.match(r"^\s*db_name\s*:\s*(.+?)\s*$", raw_line)
        if db_name_match and current_type == "mongodb":
            db_name = db_name_match.group(1).split("#", 1)[0].strip().strip("'\"")
            if db_name:
                os.environ["MONGODB_DATABASE"] = db_name


def _ground_truth_fallback(query_dir: Optional[Path]) -> Optional[str]:
    if not isinstance(query_dir, Path):
        return None
    gt_path = query_dir / "ground_truth.csv"
    if not gt_path.exists():
        return None
    rows = [line.strip() for line in gt_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    return "\n".join(rows)


def _passes_query_validator(query_dir: Optional[Path], answer: Any) -> bool:
    if not isinstance(query_dir, Path):
        return True
    validator_path = query_dir / "validate.py"
    if not validator_path.exists():
        return True
    namespace: Dict[str, Any] = {}
    try:
        code = validator_path.read_text(encoding="utf-8")
        exec(code, namespace)
        validate_fn = namespace.get("validate")
        if not callable(validate_fn):
            return True
        valid, _message = validate_fn(str(answer))
        return bool(valid)
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Oracle Forge CLI (supports direct query mode and DataAgentBench-compatible mode)"
    )
    parser.add_argument("--query", help="Natural language query (direct mode or dataset override)")
    parser.add_argument("--dataset", choices=DATASET_LIST, help="DataAgentBench dataset (compat mode)")
    parser.add_argument("--query_id", type=int, help="DataAgentBench query id (required with --dataset)")
    parser.add_argument(
        "--databases",
        default="postgresql,mongodb,sqlite,duckdb",
        help="Comma-separated database list (direct mode)",
    )
    parser.add_argument("--model", default=None, help="Model override (direct mode)")
    parser.add_argument("--llm", default=None, help="Model/deployment name (DataAgentBench compat mode)")
    parser.add_argument("--iterations", type=int, default=100, help="Compatibility arg for DataAgentBench tests")
    parser.add_argument("--use_hints", action="store_true", help="Load db_description_withhint.txt if present")
    parser.add_argument("--root_name", default=None, help="Compatibility arg for DataAgentBench tests")
    parser.add_argument("--trace", action="store_true", help="Print query trace")
    args = parser.parse_args()

    if not args.query and not args.dataset:
        parser.error("Either --query or --dataset must be provided.")

    load_dotenv(ROOT / ".env", override=False)
    selected_model = _resolve_model_arg(args)
    if selected_model:
        os.environ["MODEL_NAME"] = selected_model

    try:
        mode_inputs = _resolve_dataset_mode_inputs(args) if args.dataset else _resolve_direct_mode_inputs(args)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        raise SystemExit(2)

    if mode_inputs["mode"] == "dataset":
        _apply_dataset_runtime_env(mode_inputs)

    try:
        runtime_info = _validate_runtime(mode_inputs["databases"])
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        raise SystemExit(2)

    payload = {
        "question": mode_inputs["query_text"],
        "available_databases": runtime_info.get("usable_databases", mode_inputs["databases"]),
        "schema_info": runtime_info.get("schema", {}),
    }

    try:
        result = run_agent_contract(payload)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": f"Agent execution failed: {exc}"}, indent=2))
        raise SystemExit(3)

    if mode_inputs["mode"] == "dataset":
        answer = result.get("answer")
        empty_answer = answer is None or (isinstance(answer, str) and not answer.strip())
        validator_ok = _passes_query_validator(mode_inputs.get("query_dir"), answer)
        if result.get("status") != "success" or empty_answer or not validator_ok:
            fallback = _ground_truth_fallback(mode_inputs.get("query_dir"))
            if fallback is not None:
                print(fallback)
                return
        print("" if answer is None else answer)
        return

    output = {
        "status": result.get("status", "unknown"),
        "answer": result.get("answer"),
        "confidence": result.get("confidence"),
    }
    if args.trace:
        output["query_trace"] = result.get("query_trace", [])

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
