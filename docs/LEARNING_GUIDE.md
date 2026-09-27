# Learning Guide — every technology and module explained for beginners

Each section answers: **WHAT it is · WHY we use it · WHERE it is used · HOW it works · WHY we designed it this way · WHAT to know for viva.**

## React

- **What:** A JavaScript library for building user interfaces from reusable components that re-render when their data (state) changes.
- **Why:** The dashboard has many interactive parts (tabs, sliders, charts, polling). React keeps the screen in sync with data without manual DOM updates.
- **Where:** `frontend/src/App.tsx`, `components/*.tsx`.
- **How:** Components are functions returning JSX. `useState` stores values; `useEffect` runs side effects such as API calls or the 2-second polling timer in `ProjectView.tsx`. When state changes, React re-renders only what changed.
- **Design choice:** One component per tab keeps files small; chart tabs are lazy-loaded (`React.lazy`) so the first page load is ~249 kB instead of ~650 kB.
- **Viva:** Difference between props and state; what `useEffect` cleanup does (clearing the polling interval); why keys are needed in lists.

## TypeScript

- **What:** JavaScript with static types checked at build time.
- **Why:** API responses have many fields; types catch mistakes like reading `risk.score` instead of `risk.risk_score` before the app runs.
- **Where:** `frontend/src/lib/types.ts` mirrors backend Pydantic schemas; `tsc -b` runs in CI.
- **How:** You declare interfaces (`RiskResponse`), and the compiler checks every use. Types disappear after compilation.
- **Design choice:** `strict` mode on; types kept in one file so backend changes are easy to mirror.
- **Viva:** What `strict` does; interface vs type; types do not validate data at runtime (the backend does that).

## Vite and Tailwind CSS

- **What:** Vite is a fast dev server and bundler; Tailwind is a utility-first CSS framework.
- **Why:** Instant reloads during development; consistent spacing/colours without writing large CSS files.
- **Where:** `frontend/vite.config.ts` (dev proxy /api → :8000), `src/index.css` (design tokens in `@theme`).
- **How:** Vite serves ES modules in development and bundles/minifies for production. Tailwind generates only the classes used.
- **Design choice:** Colours are named tokens (`--color-risk-high`), so risk colours are identical everywhere.
- **Viva:** Why the dev proxy avoids CORS; what a production build outputs (`dist/`).

## Recharts

- **What:** A React charting library built on SVG.
- **Why:** Needed line/bar charts for activity, history and simulation with little code.
- **Where:** `ActivityTab`, `ContributorsTab`, `HistoryTab`, `SimulatorTab`.
- **How:** You pass an array of objects and declare axes/series as components.
- **Design choice:** Charts only display stored/calculated data; missing history shows a message instead of an invented line.
- **Viva:** Why we do not interpolate missing history.

## Python

- **What:** A general-purpose language with a strong data and web ecosystem.
- **Why:** FastAPI, pandas, scikit-learn and ReportLab are all Python, so one language covers API, analytics and ML.
- **Where:** Everything in `backend/` and `ml/`.
- **How:** Python 3.12 with type hints; dataclasses for engine results.
- **Design choice:** Pure functions for engines make them easy to test.
- **Viva:** What a virtual environment is; what type hints do (documentation + tooling, not enforcement).

## FastAPI

- **What:** A Python web framework for building APIs using type hints.
- **Why:** Automatic request validation, automatic OpenAPI/Swagger docs, dependency injection, and background tasks.
- **Where:** `backend/app/main.py`, `api/routes/*.py`, `api/deps.py`.
- **How:** A decorator maps a path to a function (`@router.post('/{project_id}/analyze')`). Parameters typed with Pydantic models are validated automatically. `Depends()` supplies the DB session or GitHub client factory; tests override these.
- **Design choice:** Analysis runs as a `BackgroundTask` returning 202 so the browser never waits on a long request; exception handlers give one error format.
- **Viva:** What dependency injection is and how we use it for testing; why 202 Accepted; where Swagger is (`/docs`).

## Pydantic

- **What:** A data-validation library using Python type hints.
- **Why:** Rejects bad input before our code runs and defines the exact JSON shape of responses.
- **Where:** `app/schemas/api.py`, `app/core/config.py` (settings from env vars).
- **How:** A class like `ProjectCreate(repository_url: str = Field(max_length=300))` validates incoming JSON; `SecretStr` hides the token in logs.
- **Design choice:** Separate schemas from database models so the API contract does not leak internal fields.
- **Viva:** Difference between a Pydantic schema and a SQLAlchemy model.

## PostgreSQL

- **What:** An open-source relational database.
- **Why:** Reliable transactions, constraints (UNIQUE, CHECK, FK cascades), JSON columns and wide hosting support.
- **Where:** Docker service `db`; connection via `DATABASE_URL`.
- **How:** Tables with primary/foreign keys; indexes on (project_id, time) speed up window queries.
- **Design choice:** Constraints enforce correctness even if application code has a bug (e.g. risk score must be 0–100).
- **Viva:** What an index is; what ON DELETE CASCADE does; ACID transactions and our rollback on failed collection.

## SQLAlchemy

- **What:** Python ORM: maps classes to tables and builds SQL safely.
- **Why:** Portable between PostgreSQL (production) and SQLite (fast local tests); parameterised queries prevent SQL injection.
- **Where:** `app/models/entities.py`, queries in services and routes.
- **How:** `select(Commit).where(Commit.project_id == id)` becomes SQL with bound parameters. Sessions track changes and commit them in a transaction.
- **Design choice:** Upserts written portably (query existing keys, then insert/update) rather than dialect-specific SQL.
- **Viva:** What an ORM is; why ORM queries prevent injection; what a session is.

## Alembic

- **What:** A database migration tool for SQLAlchemy.
- **Why:** Schema changes must be versioned and repeatable on every machine and server.
- **Where:** `backend/alembic/`, run automatically by the backend container.
- **How:** Each revision file has `upgrade()` and `downgrade()`. `alembic upgrade head` applies all pending revisions.
- **Design choice:** A test verifies upgrade/downgrade and that the migration matches the models exactly.
- **Viva:** Why not `create_all()` in production; what happens when you change a model.

## GitHub REST API

- **What:** HTTP endpoints exposing repository data as JSON.
- **Why:** It is the official, documented source of the activity data we analyse.
- **Where:** `app/services/github_client.py`, `collector.py`.
- **How:** Requests carry `Authorization: Bearer <token>`. Lists are paginated (100 per page) with a `Link` header for the next page. Headers report remaining quota; exhausted quota returns 403/429.
- **Design choice:** Page caps and a cache TTL limit calls; the token lives only on the server; 5xx errors retry with backoff; empty repositories (409) are handled.
- **Viva:** Rate limits (60/h without token, 5,000/h with); pagination; why the issues endpoint includes PRs and how we filter them.

## REST API

- **What:** An architectural style where resources (projects, runs) are addressed by URLs and manipulated with HTTP methods.
- **Why:** Simple, stateless, cacheable, and easy for the React app and tests to use.
- **Where:** All `/api/...` routes.
- **How:** POST creates (201), GET reads (200), DELETE removes (204), long work returns 202; errors use 4xx/5xx with a JSON envelope.
- **Design choice:** Nested resources under a project (`/projects/{id}/risk`) match the domain.
- **Viva:** Idempotency of GET/DELETE; meaning of 202, 409, 422, 429.

## Docker and Docker Compose

- **What:** Docker packages an app with its runtime into an image; Compose runs several containers together.
- **Why:** “Works on my machine” problems disappear; the whole stack starts with one command.
- **Where:** `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`.
- **How:** The frontend image uses a multi-stage build (Node builds, nginx serves). The backend image installs requirements, runs as a non-root user, migrates then starts uvicorn. Compose waits for the DB health check.
- **Design choice:** nginx proxies `/api` to the backend so the browser talks to one origin; the DB port is not exposed to the host.
- **Viva:** Image vs container; multi-stage builds; volumes (`pgdata`) keep data between restarts.

## GitHub Actions and CI/CD

- **What:** CI automatically builds and tests every push/PR; CD would deploy automatically.
- **Why:** Catches broken code before it reaches `main`.
- **Where:** `.github/workflows/ci.yml`.
- **How:** Three jobs: backend (ruff + pytest on a real PostgreSQL service container, coverage ≥ 85%), frontend (lint, typecheck, tests, build), docker (builds both images, validates compose).
- **Design choice:** No automatic deployment until secrets and access control are verified (brief requirement).
- **Viva:** Difference between CI and CD; what a service container is.

## Deployment

- **What:** Running the system on a server reachable by users.
- **Why:** Demo and evaluation outside a laptop.
- **Where:** `render.yaml`, docs/13_DEPLOYMENT.md.
- **How:** A Render Blueprint creates PostgreSQL, the API (Docker) and the static frontend; secrets are entered in the dashboard.
- **Design choice:** Health check endpoint; DB URL normalisation; environment-based configuration (12-factor).
- **Viva:** Environment variables vs config files; why secrets never go into git.

## pandas and NumPy

- **What:** NumPy: fast numeric arrays. pandas: tables (DataFrames) built on NumPy.
- **Why:** Medians, counts per author, weekly aggregation and dataset building are concise and correct with these libraries.
- **Where:** `engines/metrics.py` (value_counts, medians), `ml/train_dormancy.py`.
- **How:** `pd.Series(authors).value_counts()` gives commits per author, sorted; `np.median` gives robust central values.
- **Design choice:** Median instead of mean because turnaround times are skewed by a few very slow PRs.
- **Viva:** Why median is robust to outliers.

## Machine Learning (in PROSPECT)

- **What:** Algorithms that learn patterns from data to make predictions.
- **Why:** To test honestly whether historical commit patterns predict dormancy better than a simple rule.
- **Where:** `ml/`, `backend/app/ml/`.
- **How:** Supervised: features at time T → label observed after T → train on 60 repositories, test on 16 unseen repositories. Unsupervised: Isolation Forest finds unusual weeks.
- **Design choice:** ML is experimental and kept out of the score because no validated risk labels exist.
- **Viva:** Supervised vs unsupervised; data leakage; why accuracy is misleading on imbalanced data; what our results actually show.

## scikit-learn

- **What:** Python's standard classic-ML library.
- **Why:** Logistic regression, random forest, Isolation Forest, pipelines, group-aware splitting and metrics in one tested package.
- **Where:** `ml/train_dormancy.py`, `app/ml/anomaly.py`, `app/ml/dormancy.py`.
- **How:** `Pipeline([StandardScaler(), LogisticRegression()])` bundles preprocessing with the model so the same scaling is applied at prediction time. `GroupShuffleSplit` keeps each repository in only one split.
- **Design choice:** `class_weight='balanced'` for imbalance; seed 42 for reproducibility.
- **Viva:** Why scaling belongs inside the pipeline; what GroupKFold prevents.

## SHAP and explainability

- **What:** SHAP explains individual predictions by attributing them to features (Shapley values).
- **Why:** Explainability is required so users can trust and act on outputs.
- **Where:** Not a dependency. Explanations are exact: additive risk contributions; logistic-regression log-odds contributions (`coef × standardised value`).
- **How:** For linear/additive models, per-feature contributions can be computed exactly, so an approximation library is unnecessary.
- **Design choice:** We chose the simplest method that is exact for our models and documented why SHAP is not used.
- **Viva:** When SHAP would be appropriate (tree/black-box models); why correlated features make individual attributions unstable.

## Metric Engine

- **What:** The module that converts raw commits/issues/PRs/releases into 22 documented metrics.
- **Why:** Raw data is not interpretable; metrics with definitions are.
- **Where:** `backend/app/engines/metrics.py`; doc generated into docs/05_METRICS.md.
- **How:** Filters bots and future data, computes counts over 30/90/365-day windows, medians, ratios, concentration and the commit-share bus factor; returns `None` with a note when data is missing.
- **Design choice:** Definitions live next to the code; documentation is generated from them.
- **Viva:** Explain two metric formulas precisely (e.g. activity trend, bus factor estimate) and their limitations.

## Risk Engine

- **What:** The transparent model that turns metrics into a 0–100 risk score and level.
- **Why:** Decision-makers need one prioritised view with reasons.
- **Where:** `engines/risk.py`, `engines/risk_config.py`.
- **How:** Piecewise-linear interpolation per signal → mean per dimension → weighted sum with renormalised weights → level thresholds; per-signal contributions sum to the score.
- **Design choice:** Additive by design for exact explanations; configurable; config snapshot stored per run.
- **Viva:** Work through a numeric example; what coverage means; why it is not validated.

## Recommendation Engine

- **What:** Rules that map high-scoring signals to actions.
- **Why:** A score alone does not tell a team what to do.
- **Where:** `engines/recommendations.py`.
- **How:** For each signal with score ≥ 50, emit its rule (HIGH if ≥ 75); store with the RiskFactor id.
- **Design choice:** Rules are simple, reviewable and traceable; a test ensures every signal has a rule.
- **Viva:** The decision table for priority.

## What-If Simulator

- **What:** Recomputes risk with user-changed metric values.
- **Why:** Helps teams see which improvements would most change the score.
- **Where:** `engines/simulator.py`, `POST /simulate`, `SimulatorTab.tsx`.
- **How:** Validates keys/ranges, runs the same risk engine on baseline and modified metrics, returns both and the difference, stores a scenario.
- **Design choice:** Uses the exact same engine so results are consistent; always labelled SIMULATION / ESTIMATE.
- **Viva:** Why a simulation is not a prediction (changing one metric in reality changes others).
