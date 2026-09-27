# PROSPECT — Project Plan

**Predictive Software Project Risk Analysis and Decision Support System**
Team: Anurag Patwari (27), Abhrajit Pal (14), Pritam Saha (24), Anuska Nayak (22)

## 1. Environment inspection (Phase 0, recorded 17 Sep 2026)

| Item | Finding |
|---|---|
| OS | Ubuntu 24.04.4 LTS (x86_64), 4 GB RAM, 1 CPU |
| Python | 3.12.3 |
| Node / npm | 22.22.2 / 10.9.7 |
| Git | 2.43.0 |
| Docker | **Not available** in the build environment → Dockerfiles/compose are written and statically checked, but must be run on a developer machine |
| PostgreSQL | Not preinstalled → installed PostgreSQL 16 via apt so migrations and tests run against real PostgreSQL |
| GitHub API | Reachable, but the shared unauthenticated quota (60 req/h) was exhausted at start → the app must handle rate limits and strongly recommend a token |
| Existing files | Empty directory — greenfield project |

## 2. Requirements (summary — full SRS in docs/04_SRS.md)

Functional: register a GitHub repository by URL; collect commits, issues, PRs, contributors, releases; compute documented metrics; compute a transparent, configurable risk score (0–100) with level LOW/MEDIUM/HIGH/CRITICAL and health score; explain every point of the score; generate rule-based recommendations linked to factors; store every analysis run and show history; What-If simulation clearly labelled as an estimate; experimental ML (anomaly detection + dormancy model, only if defensible); PDF report.

Non-functional: token never leaves the backend; validated inputs; no stack traces in production; reproducible (Docker, pinned deps, seeded ML); tested (unit/API/integration/error/security/ML); understandable by third-year students.

## 3. Architecture

React (Vite, TS, Tailwind, Recharts) → FastAPI REST API → services (GitHub client, collector, analysis orchestrator, report) and pure engines (metrics, risk, recommendations, simulator, ML) → PostgreSQL via SQLAlchemy 2 + Alembic. Details: docs/08_SYSTEM_ARCHITECTURE.md.

## 4. Modules and owners

| Module | Location | Primary owner |
|---|---|---|
| API, orchestration, risk engine | backend/app/api, services, engines/risk.py | Anurag |
| Frontend dashboard | frontend/ | Abhrajit |
| Metric analysis, ML experiment | backend/app/engines/metrics.py, backend/app/ml, ml/ | Pritam |
| Database, tests, Docker, CI, docs | backend/app/models, alembic, tests, .github, docs | Anuska |

## 5. Key decisions and assumptions

1. **One project = one GitHub repository** in the MVP (Project and Repository merged into one table).
2. **No user authentication in the MVP.** The system stores only public repository data and runs as a single-team tool. Adding login would add password storage and session security surface without serving the core research question. Documented in docs/12_SECURITY.md with a migration path. Deploy privately or behind a platform access control.
3. **Rule-based risk engine is the primary system.** Its weights and thresholds are heuristic defaults informed by the literature, *not* empirically validated. The UI and report say so.
4. **ML is experimental and kept honest:** (a) unsupervised anomaly detection over weekly activity, never mixed into the score; (b) a supervised "dormancy within 180 days" model built from real commit histories with a temporally separated, self-derived label and repository-grouped splits. Results are reported as measured, with limitations.
5. **SHAP is not used in the served model.** The served model is logistic regression, whose per-feature log-odds contributions are exact; SHAP would add a heavy dependency for no extra fidelity. (Justification in docs/07_ML_METHODOLOGY.md.)
6. **Collection caps** (pages per endpoint) protect the API quota; truncation is recorded and shown.
7. **Personal data minimisation:** only GitHub logins are stored; commit authors without a linked account are stored as a salted hash, never as e-mail/name.

## 6. Development phases and milestones

| Phase | Deliverable | Milestone |
|---|---|---|
| 1–3 | Structure, config, DB models, Alembic, FastAPI skeleton | M1: `/api/health` green on PostgreSQL |
| 4–5 | GitHub client + collector with pagination, rate-limit handling | M2: real repository collected |
| 6–8 | Metric, risk, recommendation engines | M3: explainable score via API |
| 9–12 | Frontend dashboard, history, simulator | M4: end-to-end demo in browser |
| 13–15 | ML experiment, explanations, PDF report | M5: model card + report download |
| 16–20 | Tests, security, Docker, CI, deployment config | M6: CI green |
| 21–23 | Documentation, diagrams, viva, presentation | M7: submission ready |

Development model: iterative-incremental (each phase produces a runnable increment).

## 7. Risks to the project itself

| Risk | Mitigation |
|---|---|
| GitHub rate limits | Token support, page caps, cache TTL, clear 429 errors |
| No defensible ML labels | Self-derived temporal label; if weak, report honestly — rule engine stays primary |
| Over-engineering | Pure-function engines, one table per concept, no microservices |
| Unverifiable claims | FACT / INTERPRETATION / IMPLEMENTATION / FINDING labelling in research docs |
| Docker not testable here | Documented commands; CI builds images on GitHub |
