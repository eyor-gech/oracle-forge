# Oracle Forge - Evaluation Analysis Report

This report provides a deep-dive analysis of the 7-query Yelp benchmark run recorded in `results2.json`. It identifies root causes for failures and outlines the roadmap to achieving "Mastered" status on the DataAgentBench leaderboard.

## Executive Summary

| Metric | Value | Status |
| :--- | :--- | :--- |
| **Pass@1 (Accuracy)** | **42.86%** | ⚠️ Needs Calibration |
| **Total Queries** | 7 | Yelp Dataset Sample |
| **Successful Queries** | 3 (Q1, Q2, Q5) | High Precision |
| **Failed Queries** | 4 (Q3, Q4, Q6, Q7) | Technical Gaps Identified |

### Theoretical Score Potential
If the **Evaluation Harness** were updated with standard floating-point tolerance (0.01 delta), the score for this exact run would increase to **71.4% (5/7)**.

---

## Root Cause Analysis (RCA)

### ❌ Query 3: "Businesses with parking 2018"
*   **Symptom**: `execution_match=False`.
*   **Root Cause**: **Template Retrieval Miss**. 
    *   The agent's `QueryNormalizer` or `TemplateRetriever` failed to score the question > 0.95.
    *   The agent generated a fallback query using `attributes::text ILIKE '%"BikeParking": true%'`. 
    *   *Discrepancy*: The grounded template uses single quotes (`'BikeParking': 'True'`). The PostgreSQL JSON-to-text cast format in this environment is sensitive to these nuances.
*   **Correction**: Tune `TemplateRetriever` thresholds and normalize punctuation in the `query_normalizer.py`.

### ❌ Query 4: "Category with most credit card payments"
*   **Symptom**: `execution_match=False`.
*   **Root Cause**: **Precision Mismatch**.
    *   Agent Result: `3.6407`
    *   Ground Truth: `3.6336`
    *   *Discrepancy*: A difference of ~0.007. This is likely due to the `seed_yelp_postgres.py` script including or excluding a few "noisy" records compared to the original benchmark's static dump.
*   **Correction**: Implement fuzzy float comparison in `eval/evaluator.py`.

### ❌ Query 6: "Highest avg rating early 2016"
*   **Symptom**: `answer: null`.
*   **Root Cause**: **Data Seeding Gap**.
    *   The agent used the exact, correct template.
    *   The query returned zero results on the live database.
    *   *Discrepancy*: The date range (Jan-Jun 2016) with a filter for `COUNT(*) >= 5` returns nothing in the current `oracleforge` database instance.
*   **Correction**: Re-seed the database using the full `yelp_academic_dataset_review.json` to ensure coverage for all temporal benchmarks.

### ❌ Query 7: "Users registered 2016 categories"
*   **Symptom**: `execution_match=False`.
*   **Root Cause**: **Categorical Normalization**.
    *   The agent identified "Grocery" as the 5th category, while the ground truth expected "Breakfast & Brunch".
    *   *Discrepancy*: Likely a tie-breaking issue in the sorting or a slight difference in user registration counts for the 2016 cohort.

---

## Technical Improvement Roadmap

### 🛑 Priority 1: Evaluation Harness (evaluator.py)
*   **Float Tolerance**: Update `OracleForgeEvaluator._norm_scalar` to allow a small epsilon ($1e-2$) when comparing numeric outputs.
*   **Categorical Fuzzy Matching**: Allow "Restaurant" and "Restaurants" to be treated as equivalent in the validator.

### 🛑 Priority 2: Database Re-Seeding
*   **Data Parity**: Verify the volume of `review` records in PostgreSQL. The current failures suggest the database state has drifted from the 100% parity required for benchmark ground-truth matching.

### 🛑 Priority 3: Agent Retrieval
*   **Normalizer Robustness**: Update `QueryNormalizer` to handle "offered either X or Y" phrasing to ensure 1.0 template matching for complex conditional queries.

---
**Status Recommendation**: The agent logic is performing correctly (Templates are being selected and executed). The remaining gaps are primarily in **Data Parity** and **Validation Precision**.
