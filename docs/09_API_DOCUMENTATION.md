# 09 — REST API

Interactive documentation: **`/docs`** (Swagger UI) and **`/openapi.json`** on the running backend.

**Errors** always use `{"error": {"code": "...", "message": "...", ...extra}}`.

| Code | HTTP | Meaning |
|---|---|---|
| VALIDATION_ERROR | 422 | Body/query failed validation; `details[]` lists fields |
| INVALID_REPOSITORY_URL | 422 | URL not of the form github.com/owner/repo |
| INVALID_SIMULATION | 422 | Unknown metric or out-of-range value |
| PROJECT_NOT_FOUND / RUN_NOT_FOUND | 404 | Unknown id |
| NO_COMPLETED_ANALYSIS | 404 | Run an analysis first |
| REPOSITORY_NOT_FOUND | 404 | Repository missing or private |
| PROJECT_EXISTS | 409 | Already registered; `project_id` included |
| ANALYSIS_IN_PROGRESS | 409 | A run is active; `run_id` included |
| GITHUB_RATE_LIMITED | 429 | GitHub quota exhausted; `reset_at` included |
| GITHUB_UNAVAILABLE / GITHUB_ERROR | 503 / 502 | GitHub failure after retries |
| DATABASE_UNAVAILABLE | 503 | Health check failed |
| INTERNAL_ERROR | 500 | Unexpected error (details only in server logs) |

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness + DB check; reports whether a token is configured (never the token) |
| GET | `/api/metrics/definitions` | All metric definitions |
| GET | `/api/risk-model` | Active weights/thresholds and simulatable metric ranges |
| GET | `/api/ml/model-card` | Measured results of the experimental model |
| POST | `/api/projects` | Register repository `{ "repository_url": "https://github.com/pallets/flask" }` → 201 |
| GET | `/api/projects` | List projects with latest risk summary and active run |
| GET | `/api/projects/{id}` | One project |
| DELETE | `/api/projects/{id}` | Delete project and all data → 204 |
| POST | `/api/projects/{id}/analyze?force=false` | Start analysis → 202 run |
| GET | `/api/projects/{id}/runs` | Runs, newest first |
| GET | `/api/projects/{id}/runs/{run_id}` | Poll run status |
| GET | `/api/projects/{id}/metrics?run_id=` | Metric values + definitions (latest completed run by default) |
| GET | `/api/projects/{id}/risk?run_id=` | Score, level, dimensions, factors, top factors, ML output, disclaimer |
| GET | `/api/projects/{id}/recommendations?run_id=` | Recommendations with `risk_factor_id` |
| GET | `/api/projects/{id}/history` | Completed runs + 7/30/90-day changes (null when no real earlier run) |
| GET | `/api/projects/{id}/activity` | 52 weekly rows + anomaly output |
| GET | `/api/projects/{id}/contributors` | 90-day commit shares, all-time top contributors |
| POST | `/api/projects/{id}/simulate` | `{ "overrides": {"median_pr_turnaround_days": 2} }` → simulation |
| GET | `/api/projects/{id}/report?run_id=` | PDF download |

## Example session (curl)
```bash
curl -X POST localhost:8000/api/projects -H 'Content-Type: application/json' \
     -d '{"repository_url":"https://github.com/pallets/click"}'
curl -X POST 'localhost:8000/api/projects/1/analyze'
curl localhost:8000/api/projects/1/runs/1          # repeat until "COMPLETED"
curl localhost:8000/api/projects/1/risk
curl -X POST localhost:8000/api/projects/1/simulate -H 'Content-Type: application/json' \
     -d '{"overrides":{"median_pr_turnaround_days":1,"top_contributor_share":0.3}}'
curl -o report.pdf localhost:8000/api/projects/1/report
```
