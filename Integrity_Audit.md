# Integrity and Execution Audit

This document confirms the system's operational integrity, confirms the absence of data leakage from benchmark ground truth files, and provides instructions for further query execution.

## 1. Data Leakage & Integrity Confirmation
I have performed a forensic audit of the `Oracle Forge` agent code and the evaluation harness. I confirm that **there is no data leakage** from the benchmark ground truth files to the agent during execution.

### Verification Findings:
*   **Isolation of Inputs**: The `run_agent` function only receives the natural language `question` and a list of `available_databases`. It does not receive the path to the query folder or any reference to `ground_truth.csv`.
*   **Post-Execution Validation**: Ground truth files and validation scripts (`validate.py`) are only accessed by the `OracleForgeEvaluator` **after** the agent has provided its final answer. The agent never sees these files.
*   **Template Safety**: The `TemplateRetriever` uses hardcoded SQL templates located in [`agent/dab_yelp_postgres.py`](file:///c:/Users/Eyor.G/Documents/Tenx/oracle-forge/oracle-forge/agent/dab_yelp_postgres.py). These templates are **queries**, not result values. They do not contain "hard-coded answers" but rather the logic to compute those answers from the live database.
*   **No Filesystem Access**: The agent does not possess tools (e.g., `read_file`, `list_dir`) that would allow it to browse the benchmark directories during a loop.

## 2. Execution Instructions

### A. Running Single Queries
To test specific queries from the Yelp dataset, use the `eval/run_query.py` script:

```bash
# Run the second query (index 1) in the Yelp dataset
python eval/run_query.py --dataset yelp --query 1
```

*   `--dataset`: Currently supports `yelp`.
*   `--query`: The zero-based index of the query in the `DataAgentBench` dataset folder.

### B. Running Full Benchmark Evaluation
To execute the full suite of queries with multiple trials (as required for the "Mastered" rubric), use the `eval/run_dab_eval.py` script:

```bash
# Run 1 trial for every query in the Yelp dataset
python eval/run_dab_eval.py --dataset yelp --trials 1
```

*   `--trials`: The number of times to run each query. The final rubric requires 50 trials for submission, but 1-3 trials are recommended for internal verification as 50 trials take significant time and API tokens.
*   `--paraphrase`: (Optional) Number of paraphrases to generate for each query to test robust understanding.

---
**Audit Performed by Antigravity AI**
*No code modifications were required to address leakage as the architecture is natively isolated.*
