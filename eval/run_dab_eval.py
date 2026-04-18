from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.main import run_agent
from eval.evaluator import OracleForgeEvaluator
from eval.metrics import wilson_ci
from eval.regression_gate import evaluate_regression_gate

try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None  # type: ignore[assignment]


def _load_baseline_pass_at_1(score_log_path: Path) -> float | None:
    if not score_log_path.exists():
        return None
    baseline = None
    for line in score_log_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if entry.get("stage") == "baseline" and entry.get("pass@1") is not None:
            baseline = float(entry["pass@1"])
    return baseline


def _generate_paraphrases(question: str, count: int, model_name: str, api_key: str) -> List[str]:
    if count <= 0 or not api_key or Groq is None:
        return []
    client = Groq(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model=model_name,
            temperature=0.2,
            max_tokens=220,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "Generate concise semantic paraphrases with same intent. Return JSON: {\"paraphrases\": [...]} only.",
                },
                {"role": "user", "content": json.dumps({"question": question, "count": count})},
            ],
        )
        payload = json.loads((completion.choices[0].message.content or "{}").strip())
        paraphrases = payload.get("paraphrases", [])
        if not isinstance(paraphrases, list):
            return []
        out = [str(item).strip() for item in paraphrases if str(item).strip()]
        return out[:count]
    except Exception:
        return []


def _to_natural_language_answer(answer: Any) -> str:
    if answer is None:
        return ""
    if isinstance(answer, str):
        return answer.strip()
    if isinstance(answer, (int, float, bool)):
        return str(answer)
    if isinstance(answer, list):
        if all(not isinstance(item, (dict, list)) for item in answer):
            return ", ".join(str(item) for item in answer)
        return json.dumps(answer, ensure_ascii=False)
    if isinstance(answer, dict):
        if len(answer) == 1:
            value = next(iter(answer.values()))
            if not isinstance(value, (dict, list)):
                return str(value)
        return json.dumps(answer, ensure_ascii=False)
    return str(answer)


def _db_binding_verdict(
    query_trace: List[Dict[str, Any]],
    used_databases: List[Dict[str, Any]],
    expected_db_types: List[str],
    expected_logical_databases: List[str],
) -> Dict[str, Any]:
    expected_types = {str(item).strip().lower() for item in expected_db_types if str(item).strip()}
    expected_logical = {str(item).strip() for item in expected_logical_databases if str(item).strip()}

    observed_types = {
        str(item.get("database", "")).strip().lower()
        for item in used_databases
        if isinstance(item, dict) and str(item.get("database", "")).strip()
    }
    observed_logical: set[str] = set()
    for event in query_trace:
        if not isinstance(event, dict):
            continue
        for logical in event.get("logical_db_targets", []) or []:
            name = str(logical).strip()
            if name:
                observed_logical.add(name)
        for local_event in event.get("local_execution_trace", []) or []:
            if isinstance(local_event, dict):
                name = str(local_event.get("logical_db", "")).strip()
                if name:
                    observed_logical.add(name)

    unexpected_types = sorted(observed_types - expected_types)
    unexpected_logical = sorted(observed_logical - expected_logical) if expected_logical else []
    has_logical_evidence = bool(observed_logical)
    passed = has_logical_evidence and not unexpected_types and not unexpected_logical

    if passed:
        reason = "dataset-scoped DB binding verified via logical DB evidence"
    elif not has_logical_evidence:
        reason = "no dataset logical DB evidence in trace; likely not using dataset-local db_config"
    elif unexpected_types:
        reason = f"observed unexpected database types: {unexpected_types}"
    else:
        reason = f"observed unexpected logical DB targets: {unexpected_logical}"

    return {
        "passed": passed,
        "reason": reason,
        "expected_db_types": sorted(expected_types),
        "observed_db_types": sorted(observed_types),
        "expected_logical_databases": sorted(expected_logical),
        "observed_logical_databases": sorted(observed_logical),
        "unexpected_db_types": unexpected_types,
        "unexpected_logical_databases": unexpected_logical,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DataAgentBench evaluation")
    parser.add_argument("--dataset", default=os.getenv("DAB_DATASET", "yelp"), help="Dataset name (default: yelp)")
    parser.add_argument("--trials", type=int, default=int(os.getenv("DAB_TRIALS_PER_QUERY", "50")), help="Trials per query")
    parser.add_argument("--paraphrase", type=int, default=0, help="Optional paraphrases per query")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=False)

    eval_root = ROOT / "eval"
    eval_root.mkdir(parents=True, exist_ok=True)
    score_log_path = eval_root / "score_log2.jsonl"

    evaluator = OracleForgeEvaluator(repo_root=ROOT)
    queries = evaluator.load_dataagentbench_queries(dataset=args.dataset)

    all_query_reports: List[Dict[str, Any]] = []
    paraphrase_reports: List[Dict[str, Any]] = []
    total_first_correct = 0
    total_trial_correct = 0
    total_trials = 0

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    model_name = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

    for query in queries:
        trials_report: List[Dict[str, Any]] = []
        first_correct = False

        for trial in range(args.trials):
            result = run_agent(
                question=query["question"],
                available_databases=query["available_databases"],
                schema_info=query["schema_info"],
                db_config_path=query.get("db_config_path"),
            )
            valid, message = evaluator._validate_answer(query, result)
            trial_trace = result.get("query_trace", result.get("trace", []))
            trial_used = result.get("used_databases", [])
            binding_verdict = _db_binding_verdict(
                query_trace=trial_trace if isinstance(trial_trace, list) else [],
                used_databases=trial_used if isinstance(trial_used, list) else [],
                expected_db_types=query.get("available_databases", []),
                expected_logical_databases=query.get("expected_logical_databases", []),
            )
            if trial == 0:
                first_correct = bool(valid)
            if valid:
                total_trial_correct += 1
            total_trials += 1
            trials_report.append(
                {
                    "trial": trial + 1,
                    "correct": bool(valid),
                    "validation_message": message,
                    "status": result.get("status"),
                    "answer": result.get("answer"),
                    "answer_text": _to_natural_language_answer(result.get("answer")),
                    "confidence": result.get("confidence"),
                    "query_trace": trial_trace,
                    "token_usage": result.get("token_usage", {}),
                    "used_databases": trial_used,
                    "db_binding_verdict": binding_verdict,
                }
            )

        if first_correct:
            total_first_correct += 1

        all_query_reports.append(
            {
                "id": query["id"],
                "question": query["question"],
                "first_trial_correct": first_correct,
                "trial_accuracy": round(sum(1 for item in trials_report if item["correct"]) / max(1, args.trials), 4),
                "trials": trials_report,
            }
        )

        if args.paraphrase > 0:
            paraphrases = _generate_paraphrases(query["question"], args.paraphrase, model_name, groq_key)
            for idx, para in enumerate(paraphrases, start=1):
                para_result = run_agent(
                    question=para,
                    available_databases=query["available_databases"],
                    schema_info=query["schema_info"],
                    db_config_path=query.get("db_config_path"),
                )
                para_valid, para_msg = evaluator._validate_answer(query, para_result)
                paraphrase_reports.append(
                    {
                        "query_id": query["id"],
                        "paraphrase_index": idx,
                        "paraphrase": para,
                        "correct": bool(para_valid),
                        "validation_message": para_msg,
                        "status": para_result.get("status"),
                        "answer": para_result.get("answer"),
                        "answer_text": _to_natural_language_answer(para_result.get("answer")),
                        "confidence": para_result.get("confidence"),
                        "query_trace": para_result.get("query_trace", para_result.get("trace", [])),
                    }
                )

    total_queries = len(queries)
    pass_at_1 = round(total_first_correct / max(1, total_queries), 4)
    overall_trial_accuracy = round(total_trial_correct / max(1, total_trials), 4)
    ci_low, ci_high = wilson_ci(total_first_correct, total_queries)
    total_binding_checks = 0
    passed_binding_checks = 0
    for query_report in all_query_reports:
        for trial in query_report.get("trials", []):
            verdict = trial.get("db_binding_verdict", {})
            if isinstance(verdict, dict) and "passed" in verdict:
                total_binding_checks += 1
                if verdict.get("passed"):
                    passed_binding_checks += 1
    db_binding_pass_rate = round(passed_binding_checks / max(1, total_binding_checks), 4)

    results = {
        "dataset": f"DataAgentBench {args.dataset}",
        "dataset_path": str(ROOT / "DataAgentBench"),
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_queries": total_queries,
        "trials_per_query": args.trials,
        "correct_first_answers": total_first_correct,
        "correct_trials": total_trial_correct,
        "total_trials": total_trials,
        "pass@1": pass_at_1,
        "pass@1_ci95": [round(ci_low, 4), round(ci_high, 4)],
        "overall_trial_accuracy": overall_trial_accuracy,
        "db_binding_summary": {
            "checks": total_binding_checks,
            "passed": passed_binding_checks,
            "pass_rate": db_binding_pass_rate,
            "verdict": "PASS" if total_binding_checks > 0 and passed_binding_checks == total_binding_checks else "FAIL",
        },
        "queries": all_query_reports,
    }

    results_path = eval_root / "results2.json"
    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    dataset_results_path = eval_root / f"results2_{args.dataset}.json"
    dataset_results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.paraphrase > 0:
        paraphrase_path = eval_root / "paraphrase_results.json"
        paraphrase_path.write_text(
            json.dumps(
                {
                    "dataset": args.dataset,
                    "paraphrase_per_query": args.paraphrase,
                    "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "results": paraphrase_reports,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    score_entry = {
        "stage": "final",
        "dataset": f"DataAgentBench {args.dataset}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_queries": total_queries,
        "trials_per_query": args.trials,
        "correct_first_answers": total_first_correct,
        "correct_trials": total_trial_correct,
        "total_trials": total_trials,
        "pass@1": pass_at_1,
        "pass@1_ci95": [round(ci_low, 4), round(ci_high, 4)],
        "overall_trial_accuracy": overall_trial_accuracy,
    }
    with score_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(score_entry, ensure_ascii=False) + "\n")

    baseline = _load_baseline_pass_at_1(score_log_path)
    if baseline is None:
        baseline = pass_at_1
    gate = evaluate_regression_gate(current_pass_at_1=pass_at_1, baseline_pass_at_1=baseline, max_drop=0.02)

    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "total_queries": total_queries,
                "trials_per_query": args.trials,
                "pass@1": pass_at_1,
                "pass@1_ci95": [round(ci_low, 4), round(ci_high, 4)],
                "overall_trial_accuracy": overall_trial_accuracy,
                "db_binding_summary": results["db_binding_summary"],
                "regression_gate": gate,
                "results_path": str(results_path),
                "dataset_results_path": str(dataset_results_path),
                "score_log_path": str(score_log_path),
            },
            indent=2,
        )
    )

    if not gate["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
