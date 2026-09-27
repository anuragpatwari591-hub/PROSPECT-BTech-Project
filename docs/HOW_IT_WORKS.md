# How PROSPECT Works — from click to report

## The journey

**"I open the application."** The browser loads a small React app (served by nginx in Docker, or Vite in development). It immediately calls `GET /api/projects` to show the repositories already registered.

For every step below: **WHAT** happens, **WHY**, **WHERE** in the code, and **HOW**.

### 1. User → React
- **What:** I paste `https://github.com/pallets/click` and select *Add repository*.
- **Why:** The repository is the unit of analysis.
- **Where:** `frontend/src/components/Sidebar.tsx` (`AddProjectForm`).
- **How:** A regular expression checks the format first, so obvious typos never reach the server. Then `api.createProject()` sends `POST /api/projects`.

### 2. React → API
- **What:** The FastAPI backend receives JSON.
- **Why:** The browser must never talk to GitHub directly — that would expose the token.
- **Where:** `backend/app/api/routes/projects.py::create_project`.
- **How:** Pydantic validates the body; `parse_repo_url` extracts `owner`/`repo`; a case-insensitive duplicate check returns 409 with the existing id; one GitHub call confirms the repository exists; the project row and an audit log entry are saved.

### 3. API → GitHub
- **What:** I select *Run first analysis*. The API creates an `AnalysisRun` (PENDING), returns **202**, and starts a background task.
- **Why:** Collection can take tens of seconds; the browser should not hang.
- **Where:** `analyze` route → `services/analysis.py::execute_run` → `services/collector.py::collect` → `services/github_client.py`.
- **How:** The client sends authenticated requests (token from the server environment), follows `Link: rel="next"` pagination up to the page cap, stops early for old PRs, retries 5xx twice, and turns 403/429 quota errors into a `RateLimited` error with the reset time.

### 4. Data collection
- **What:** Repository metadata, commits (last 365 days), open issues, issues closed in the window, open and recently updated PRs, sizes for the 15 latest merged PRs, contributors, releases.
- **Why:** These are the observable traces of development activity.
- **Where:** `collector.py`.
- **How:** If data was collected less than 30 minutes ago and *force* is off, collection is skipped (cache).

### 5. Data processing (normalisation)
- **What:** Raw JSON becomes clean rows.
- **Why:** GitHub quirks would corrupt metrics otherwise.
- **Where:** `normalize_commit`, `normalize_issue`, `normalize_pull`.
- **How:** PRs are removed from the issue list; bots are flagged; commit authors without accounts become `unlinked-<hash>` (no e-mails stored); timestamps are parsed to UTC; drafts are excluded from releases.

### 6. Database
- **What:** Rows are upserted into `commits`, `issues`, `pull_requests`, `releases`, `contributors`.
- **Why:** Enables caching, charts, and re-analysis without new API calls.
- **Where:** `models/entities.py`, `_upsert` in `collector.py`.
- **How:** Existing rows (matched by project + SHA/number/id) are updated, new ones inserted, all in one transaction — on any error everything is rolled back and the run becomes FAILED with a clear code.

### 7. Metric Engine
- **What:** 22 metrics, e.g. commits in 90 days, activity trend, median PR turnaround, top-contributor share.
- **Why:** Numbers with definitions are interpretable; raw lists are not.
- **Where:** `engines/metrics.py::compute_metrics`.
- **How:** Pure calculations over time windows; missing data gives `None` plus a note. Each value is stored in `repository_metrics` for this run.

### 8. Risk Engine
- **What:** Risk score, level, health score, coverage, dimension scores, per-signal contributions.
- **Why:** One prioritised, explainable view.
- **Where:** `engines/risk.py`, thresholds in `risk_config.py`.
- **How:** Each signal: metric → 0–100 via interpolation. Each dimension: mean of its signals. Overall: weighted sum (weights rescaled if a dimension has no data). Contributions add up to the score. Stored in `risk_assessments` and `risk_factors` together with the configuration used.

### 9. ML (experimental)
- **What:** (a) unusual weeks via Isolation Forest; (b) probability of no commits in the next 180 days via logistic regression.
- **Why:** To add pattern-based signals *and* to test honestly whether ML helps.
- **Where:** `app/ml/anomaly.py`, `app/ml/dormancy.py`, trained by `ml/train_dormancy.py`.
- **How:** Outputs are stored in `analysis_runs.ml_output` and shown in their own tab. They never change the risk score.

### 10. Explainability
- **What:** Every point of the score is traced to a signal, its metric value and the threshold used.
- **Why:** Users must understand *why* before acting.
- **Where:** `SignalResult.explanation`, `ScoreStrip.tsx`, `FactorsTab.tsx`, `ExperimentalTab.tsx`.
- **How:** Additive model → exact contributions; logistic regression → exact log-odds contributions.

### 11. Recommendations
- **What:** Actions like "Reduce pull request review time".
- **Why:** Turns diagnosis into next steps.
- **Where:** `engines/recommendations.py`.
- **How:** Signal score ≥ 50 triggers its rule (≥ 75 = high priority); stored with the id of the triggering factor.

### 12. What-If
- **What:** I move "Median PR turnaround" from 6 to 2 days and select *Simulate*.
- **Why:** Shows which improvements matter most to the model.
- **Where:** `engines/simulator.py`, `SimulatorTab.tsx`.
- **How:** Same risk engine on modified metrics; result labelled SIMULATION / ESTIMATE; scenario saved.

### 13. Dashboard
- **What:** While the run is in progress the UI polls `GET /runs/{id}` every 2 s; then it loads `/risk`, `/metrics`, `/recommendations`, and (per tab) `/activity`, `/contributors`, `/history`.
- **Where:** `ProjectView.tsx` and tab components.

### 14. Report
- **What:** *Download PDF report* calls `GET /report`.
- **Where:** `services/report.py`.
- **How:** ReportLab builds an A4 PDF: scores, contribution bar, top factors, recommendations, all metrics with definitions, history chart (if ≥ 2 runs), simulations, experimental ML output, methodology and limitations.

---

## 2-minute explanation
PROSPECT is a web application that estimates software project risk from GitHub activity and explains its reasoning. You paste a repository URL. The backend collects commits, issues, pull requests, contributors and releases through the GitHub API, stores them in PostgreSQL, and computes 22 documented metrics such as PR turnaround time and contributor concentration. A transparent rule-based engine converts those metrics into a 0–100 risk score across five dimensions, and because the model is additive, the dashboard shows exactly how many points each factor contributes. Each high factor triggers a recommendation. Users can run what-if simulations, see history across repeated analyses, and download a PDF report. We also ran an honest ML experiment predicting project dormancy; it ranked projects well but did not clearly beat a simple rule, so it is shown as experimental and kept out of the score.

## 5-minute explanation
**Problem:** warning signs of project trouble appear in development data, but existing views are either raw charts or unexplained scores.
**Solution:** a three-tier system — React frontend, FastAPI backend, PostgreSQL.
**Pipeline:** validate URL → collect with pagination, rate-limit handling and caching → normalise (remove PRs from issues, flag bots, hash unlinked authors) → store → metrics → risk → recommendations → ML → dashboard/report.
**Risk model:** 13 signals in 5 weighted dimensions; each signal is interpolated between thresholds; missing dimensions are excluded and weights renormalised; the score is the weighted sum, and contributions add up to it. Levels: LOW/MEDIUM/HIGH/CRITICAL at 25/50/75. The thresholds are our heuristics and are not validated — we say so in the UI.
**Explainability & action:** factor list with metric values and threshold explanations; recommendations tied to factors; what-if simulator using the same engine.
**ML:** there is no dataset of "risky projects", so we did not fabricate one. Instead we predicted an observable outcome — no commits in the next 180 days — from commit histories of 76 repositories, with repository-grouped splits and baselines. Logistic regression reached ROC-AUC 0.95 and PR-AUC 0.38 on 16 held-out repositories, versus 0.91/0.24 for a one-line rule, but confidence intervals overlap, so we claim no improvement.
**Quality:** 111 backend tests on PostgreSQL (97% coverage), 13 frontend tests, security tests, CI, Docker.

## 10-minute explanation
Use the 5-minute version, then add:
1. **Demo walk-through** (see README "Demo"): add repository → analysis → headline strip → factors → recommendations → what-if → history → PDF.
2. **Data engineering details:** endpoint list, page caps, cache TTL, 409 empty repository, rollback on failure, upserts keyed by natural GitHub keys.
3. **Metric examples with formulas:** activity trend `(c30 − c60/2)/(c60/2)×100`; commit-share bus factor = fewest authors with ≥ 50% of commits (not the Avelino et al. file-authorship algorithm).
4. **Worked risk example:** turnaround 9 days → signal 75; PR dimension mean; weight 0.20 renormalised to 0.235 when releases are missing; contribution = 0.235 × 75 / 4 = 4.4 points.
5. **ML methodology:** label construction, leakage controls, class imbalance (2.5% positives), why accuracy (98% for "always no") is meaningless, cluster bootstrap CIs, why LR is served (exact explanations).
6. **Security:** token server-side only; tested that it never appears in responses; validation; security headers; no authentication by explicit decision.
7. **Limitations and future work:** unvalidated thresholds; GitHub-only view; convenience ML sample; next step is validation with maintainer judgements.

## Technical explanation
FastAPI app factory with CORS allow-list, security-header middleware and typed exception handlers. Dependencies (`get_db`, `get_client_factory`, `get_session_factory`) are injected and overridden in tests. The analysis route persists a PENDING run and schedules `execute_run` via `BackgroundTasks`; that function uses a fresh session, catches `GitHubError` subclasses into run error codes, and rolls back partial collection. `GitHubClient` wraps `httpx.Client` with retries, `Link` pagination and quota detection; tests inject `httpx.MockTransport` serving a fake GitHub. Engines are pure dataclass-returning functions. Frontend state is local React state with a small `useAsync` hook; chart tabs are code-split.

## Architecture explanation
Layered: presentation (React) → API (routes/schemas) → application services (orchestrator, collector, report) → domain engines (metrics, risk, recommendations, simulator, ML) → persistence (SQLAlchemy/PostgreSQL) and integration (GitHub client). Dependencies point inward: engines know nothing about HTTP or databases. Deployment: three containers (nginx SPA + proxy, API, PostgreSQL) or Render Blueprint.

## ML explanation
Two experimental components. Isolation Forest over 52 weekly activity vectors, filtered by robust z ≥ 3 so every flag has a reason. Dormancy classifier: 8 commit-history features at cutoff T; label = zero commits in (T, T+180]; 3,533 samples from 76 repositories; GroupShuffleSplit by repository; GroupKFold CV for selection; balanced class weights; evaluated against prior and recency-rule baselines with repository-level bootstrap CIs. Served model: standardised logistic regression; explanation = coefficient × standardised value in log-odds. Result: no statistically supported improvement over the rule → experimental only.

## Database explanation
13 tables. Raw activity keyed per project with UNIQUE natural keys; derived results per analysis run; CHECK constraints for states, levels and score range; composite indexes for time-window queries; cascading deletes; JSON only for whole-document data. Alembic migration verified against models in tests.

## Security explanation
Secrets in environment variables (`SecretStr`), `.env` git-ignored, token never serialised (tested across all endpoints including the PDF). Pydantic + regex validation, ORM parameter binding, simulation whitelist. Security headers and strict CORS. Uniform errors without stack traces. Non-root container, private DB network. Audit log without personal data. Personal data minimised (hashed unlinked authors). No authentication in v1.0, with documented risk and mitigation.

## Deployment explanation
`docker compose up --build` runs PostgreSQL (health-checked), backend (migrates then serves) and nginx frontend (proxies `/api`). CI on GitHub Actions lints, tests on a PostgreSQL service container, builds the frontend and both Docker images. Cloud: `render.yaml` Blueprint provisions managed PostgreSQL, a Docker web service with `/api/health` health checks, and a static site; secrets are entered in the dashboard, never committed.

## Research contribution explanation
We do **not** claim new algorithms. Our contribution is an open, tested integration of: documented GitHub metrics; an additive risk model with exact attribution; factor-linked recommendations; a labelled what-if simulator; and a leakage-controlled, baseline-compared ML experiment whose honest negative finding (no clear gain over a recency rule on our sample) is itself informative. Related work on truck factors (Avelino et al., 2016), project failure (Coelho & Valente, 2017) and unmaintained-project identification (Coelho et al., 2018) is acknowledged.
