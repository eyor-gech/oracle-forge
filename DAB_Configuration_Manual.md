# DataAgentBench - Configuration & Operation Manual

This manual provides instructions for preparing and running the full 54-query DataAgentBench evaluation using the Oracle Forge engine.

---

## 🏗️ Environment Preparation

### 1. Docker Sandbox
The benchmark requires a Docker container to execute Python tools safely. 
**Command:**
```bash
cd DataAgentBench
docker build -t python-data:3.12 .
```
*Note: This image includes pandas and pyarrow required for data processing.*

### 2. Python Environment
All benchmark-specific dependencies are installed in the project virtual environment.
**Key Dependencies:**
- `litellm`, `gdown`, `psycopg2-binary`, `faker`

### 3. Database Connectivity
Oracle Forge routes queries through the **MCP Toolbox**.
- **Postgres:** Ensure `oracleforge` database is running and accessible via `localhost:5432`.
- **MongoDB:** Ensure `mongodb://localhost:27017/` is active.
- **SQLite/DuckDB:** Files must be located in the paths specified in `.env`.

---

## 🚀 Running the Benchmark

### Official DAB Runner (Recommended)
Use the standard DAB runner which is now integrated with Oracle Forge's `run_agent` engine.

**Example: Single Query**
```powershell
.\venv\Scripts\python DataAgentBench\run_agent.py --dataset yelp --query_id 1 --llm gpt-4o-mini
```

**Example: AGNews Query**
```powershell
.\venv\Scripts\python DataAgentBench\run_agent.py --dataset agnews --query_id 1 --llm gpt-4o-mini
```

### Automated Batch Runner
For running the full dataset evaluation with automated result capturing:
```powershell
.\venv\Scripts\python eval\run_dab_eval.py --dataset yelp --trials 1
```

---

## 📊 Results & Validation

Logs and artifacts are stored in two locations:
1. **DAB Standard Logs:** `DataAgentBench/query_<dataset>/query<id>/logs/data_agent/`
2. **Evaluation Summary:** `eval/results2.json` and `eval/score_log2.jsonl`

To calculate total Pass@1 across trials:
```powershell
# Custom script provided in eval/ directory
.\venv\Scripts\python eval\run_dab_eval.py --summarize
```

---

## ⚠️ Troubleshooting

- **Connection Refused:** Ensure Docker and MCP Toolbox services are running.
- **Missing Data:** Run `bash download.sh` inside the `DataAgentBench` directory if databases are missing.
- **Import Error:** Ensure you are running from the project root to satisfy `sys.path` requirements.
