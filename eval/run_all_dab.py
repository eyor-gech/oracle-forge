import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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

def main() -> None:
    parser = argparse.ArgumentParser(description="Run full DataAgentBench evaluation across ALL datasets")
    parser.add_argument("--trials", type=int, default=50, help="Trials per query (default: 50)")
    args = parser.parse_args()

    eval_root = ROOT / "eval"
    eval_root.mkdir(parents=True, exist_ok=True)
    
    # We will accumulate the flattened leaderboard submission items here
    leaderboard_submission = []
    dataset_verdicts = []

    print(f"Starting complete DAB evaluation over {len(DATASET_LIST)} datasets with {args.trials} trials per query...")

    for dataset in DATASET_LIST:
        print(f"\n==============================================")
        print(f"🎬 EVALUATING DATASET: {dataset}")
        print(f"==============================================")
        
        cmd = [sys.executable, str(eval_root / "run_dab_eval.py"), "--dataset", dataset, "--trials", str(args.trials)]
        
        # Run the isolated dataset evaluation
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ [WARNING] Evaluation for dataset '{dataset}' failed with exit code {e.returncode}.")
            print("Continuing to next dataset...")
            continue
        except KeyboardInterrupt:
            print("\n🛑 Evaluation manually aborted by user.")
            break
            
        # Parse the outcome to build the flattened leaderboard submission
        result_path = eval_root / f"results2_{dataset}.json"
        if not result_path.exists():
            print(f"❌ [WARNING] Results file not found for dataset '{dataset}'!")
            continue
            
        try:
            with open(result_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            dataset_verdicts.append(
                {
                    "dataset": dataset,
                    "db_binding_summary": data.get("db_binding_summary", {}),
                    "pass@1": data.get("pass@1"),
                    "total_queries": data.get("total_queries"),
                    "trials_per_query": data.get("trials_per_query"),
                }
            )
                
            for query_entry in data.get("queries", []):
                query_id_str = str(query_entry.get("id", "")).replace("query", "")
                
                for trial_item in query_entry.get("trials", []):
                    # Zero-index the run number to match 0-49 as stated in the DAB guidelines
                    run_number = trial_item.get("trial", 1) - 1 
                    answer = trial_item.get("answer")
                    
                    submission_row = {
                        "dataset": dataset,
                        "query": query_id_str,
                        "run": str(run_number),
                        "answer": answer if answer is not None else ""
                    }
                    leaderboard_submission.append(submission_row)
                    
            print(f"✅ Successfully compiled answers for {dataset}.")
        except Exception as e:
            print(f"❌ [WARNING] Error compiling results for {dataset}: {e}")

    # Write the final array formatted strictly to the DAB Submission Standard
    submission_file = eval_root / "final_leaderboard_submission.json"
    with submission_file.open("w", encoding="utf-8") as f:
        json.dump(leaderboard_submission, f, indent=2, ensure_ascii=False)

    verdict_file = eval_root / "dataset_db_binding_verdict.json"
    with verdict_file.open("w", encoding="utf-8") as f:
        json.dump(dataset_verdicts, f, indent=2, ensure_ascii=False)
        
    print(f"\n🎉 ALL EVALUATIONS COMPLETE!")
    print(f"Compiled {len(leaderboard_submission)} total trial runs into:")
    print(f" -> {submission_file}")
    print(f"Dataset DB-binding verdicts written to:")
    print(f" -> {verdict_file}")
    print("This file matches the exact structure required for your GitHub Pull Request.")

if __name__ == "__main__":
    main()
