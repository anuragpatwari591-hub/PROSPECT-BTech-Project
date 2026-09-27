# 04 — Software Requirements Specification (IEEE 830-style, condensed)

## 1. Introduction
**Purpose.** Specifies the requirements of PROSPECT v1.0. **Definitions:** *analysis run* — one execution of collection + computation for a project; *signal* — one metric mapped to a 0–100 risk score; *dimension* — a group of signals (activity, issues, pull requests, contributors, releases); *contribution* — the points a signal adds to the overall risk score; *risk score* — 0–100, higher is riskier; *health score* — 100 − risk score.

## 2. Overall description
**Product perspective:** standalone web application (browser SPA + REST API + PostgreSQL) consuming the GitHub REST API. **User class:** a single role, "analyst" (no login in v1.0 — see docs/12_SECURITY.md). **Operating environment:** Docker Compose or any Python 3.12 / Node 22 host; modern browsers. **Constraints:** GitHub rate limits; public repositories only. **Assumptions:** one project corresponds to one repository; the default branch represents main development.

## 3. Functional requirements

| ID | Requirement | Priority | Verified by |
|---|---|---|---|
| FR-1 | The system shall accept a GitHub repository URL (or `owner/repo`) and reject invalid formats before any network call. | High | `test_parse_invalid_urls`, `test_invalid_url_is_rejected_without_calling_github` |
| FR-2 | The system shall confirm the repository exists and is public when registering it. | High | `test_unavailable_repository_404` |
| FR-3 | The system shall prevent duplicate registration (case-insensitive). | Medium | `test_duplicate_project_conflict_case_insensitive` |
| FR-4 | The system shall collect commits, issues (excluding PRs), pull requests, a sample of PR sizes, contributors and releases, following pagination up to configured caps. | High | `test_full_analysis_pipeline`, `test_pagination_*` |
| FR-5 | The system shall handle rate limits, 404, 401, 5xx (with retries), network failure and empty repositories with specific error codes. | High | `test_rate_limit_*`, `test_server_error_*`, `test_empty_repository_*` |
| FR-6 | The system shall run analyses asynchronously and expose run status for polling; only one active run per project. | High | `test_analysis_conflict_when_run_active` |
| FR-7 | The system shall reuse recently collected data within a cache TTL unless `force=true`. | Medium | `test_cache_reuses_data_and_force_refetches` |
| FR-8 | The system shall compute the 22 metrics defined in docs/05_METRICS.md and return definitions with values. | High | `test_metrics.py` |
| FR-9 | The system shall compute a risk score (0–100), level (LOW/MEDIUM/HIGH/CRITICAL), health score and coverage from configurable weights and thresholds. | High | `test_risk_engine.py` |
| FR-10 | Per-signal contributions shall sum to the risk score (± rounding). | High | `test_contributions_add_up_to_score` |
| FR-11 | Each recommendation shall reference the risk factor that triggered it. | High | `test_recommendations_reference_*` |
| FR-12 | The system shall store every run and provide history with 7/30/90-day changes only where a real earlier run exists. | High | `test_cache_reuses_data_and_force_refetches` |
| FR-13 | The system shall simulate risk under user-changed metric values, validate ranges, label output "SIMULATION / ESTIMATE", and store the scenario. | High | `test_simulation_*` |
| FR-14 | The system shall generate a downloadable PDF report with scores, factors, metrics, recommendations, history, simulations, methodology and limitations. | High | `test_report_is_a_pdf` |
| FR-15 | The system shall show experimental ML outputs (anomalies, dormancy estimate) separately from the risk score, with their status and limitations. | Medium | `test_ml.py` |
| FR-16 | The system shall delete a project and all dependent data. | Low | `test_delete_project_cascades` |

## 4. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Security | The GitHub token is read from the environment only and never returned by any endpoint (`test_token_never_appears_in_any_response`). |
| NFR-2 | Security | Production responses contain no stack traces; errors use `{error: {code, message}}`. |
| NFR-3 | Security | All DB access through the ORM with bound parameters; inputs validated with Pydantic. |
| NFR-4 | Privacy | Commit author e-mails are never stored; unlinked authors are salted hashes. |
| NFR-5 | Performance | A typical analysis with a token completes in under ~60 s for repositories within collection caps. |
| NFR-6 | Reliability | A failed collection rolls back partial data and marks the run FAILED. |
| NFR-7 | Maintainability | Engines are pure functions; backend coverage ≥ 85% enforced in CI. |
| NFR-8 | Usability | Responsive layout; loading, empty and error states; keyboard focus visible; reduced motion respected. |
| NFR-9 | Portability | `docker compose up --build` starts the full stack. |
| NFR-10 | Honesty | UI and report state that the score is heuristic and not validated, and that simulations are not predictions. |

## 5. External interfaces
GitHub REST API v2022-11-28 (HTTPS, JSON, bearer token). REST API documented at `/docs` (OpenAPI 3). PDF output (A4).
