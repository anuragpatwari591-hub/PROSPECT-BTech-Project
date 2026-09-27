# PROSPECT

**Predictive Software Project Risk Analysis and Decision Support System**
Third-year B.Tech Software Engineering project — Anurag Patwari (27), Abhrajit Pal (14), Pritam Saha (24), Anuska Nayak (22).

PROSPECT connects to a public GitHub repository, collects its development activity, turns it into documented software-engineering metrics, and produces an **explainable** risk assessment: a 0–100 risk score, a risk level, the exact contribution of every factor, linked recommendations, a What-If simulator, analysis history and a PDF report.

> **Before the demo:** set `GITHUB_TOKEN` and run `python scripts/live_smoke.py --repo https://github.com/pallets/click`. A full live analysis was never completed in our build environment because the shared IP's anonymous GitHub quota was exhausted (docs/11_TESTING.md); only the live rate-limit path was verified there.

> **Honesty notes.** The risk score is a transparent *heuristic* — its weights and thresholds are configurable and **not empirically validated**. Machine-learning outputs are **experimental**: our dormancy model did not clearly outperform a one-line rule on held-out repositories (docs/07). Simulations are estimates, not predictions.

## Features
- GitHub integration with pagination, rate-limit handling, retries, caching; token kept server-side
- 22 metrics with definitions, formulas, sources, units, interpretation and limitations
- Additive risk engine across 5 dimensions / 13 signals; contributions sum to the score
- Rule-based recommendations linked to the triggering factor
- What-If simulator (labelled SIMULATION / ESTIMATE)
- History of every run with 7/30/90-day changes (never fabricated)
- Activity and contributor-dependency charts
- Experimental ML: Isolation Forest unusual weeks; logistic-regression dormancy estimate with exact explanations
- PDF reports with methodology and limitations
- 111 backend tests (97% coverage, PostgreSQL), 13 frontend tests, CI, Docker

## Tech stack
React 19 · TypeScript · Vite · Tailwind CSS 4 · Recharts — FastAPI · Pydantic 2 · SQLAlchemy 2 · Alembic · PostgreSQL 16 — pandas · NumPy · scikit-learn — ReportLab — pytest · Vitest — Docker Compose · GitHub Actions · Render Blueprint

## Quick start (Docker)
```bash
cp .env.example .env        # set GITHUB_TOKEN, POSTGRES_PASSWORD, AUTHOR_HASH_SALT
docker compose up --build
```
Open http://localhost:8080 · API docs http://localhost:8080/docs

Create a token at GitHub → Settings → Developer settings → Fine-grained tokens (public repositories, read-only). Without a token GitHub allows only 60 requests/hour.

## Quick start (without Docker)
```bash
# terminal 1 — backend (needs PostgreSQL, or omit DATABASE_URL to use SQLite)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://prospect:<pw>@localhost:5432/prospect GITHUB_TOKEN=<token>
alembic upgrade head && uvicorn app.main:app --reload
# terminal 2 — frontend
cd frontend && npm ci && npm run dev      # http://localhost:5173
```

## Tests
```bash
cd backend && pytest --cov=app            # add TEST_DATABASE_URL=... to run on PostgreSQL
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
python scripts/live_smoke.py --repo https://github.com/pallets/click   # real GitHub, running backend
```

## Demo (5 minutes)
1. Add `https://github.com/pallets/click` → **Run first analysis**.
2. Explain the headline: score, level, health, coverage, and the "where the points come from" strip.
3. **Overview** → top factors and recommendations (each names its factor).
4. **Risk factors** → metric value, threshold explanation, points per signal. Hover a metric for its definition.
5. **What-if** → set PR turnaround to 1 day and top contributor share to 0.3 → **Simulate** → point out the estimate label.
6. Add `https://github.com/request/request` (deprecated in 2020) and compare.
7. **Re-analyse** click → **History** shows two runs (no fabricated trend).
8. **Experimental ML** → dormancy estimate and why it is experimental.
9. **Download PDF report**.
10. Show `/docs` (Swagger) and the GitHub Actions run.

## Project structure
```
prospect/
├── backend/            FastAPI app, engines, ML serving, Alembic, tests, Dockerfile
├── frontend/           React + TypeScript dashboard, tests, Dockerfile, nginx.conf
├── ml/                 Reproducible dormancy experiment (collect, train, results)
├── scripts/            Live smoke test, metrics-doc generator
├── docs/               SE documentation, diagrams, viva material
├── docker-compose.yml  Local full stack
├── render.yaml         Cloud deployment blueprint
└── .github/            CI workflow, Dependabot
```

## Documentation
See [docs/README.md](docs/README.md) for the full index (problem statement → SRS → metrics → risk model → ML → architecture → API → database → testing → security → deployment → manuals → limitations → future scope, plus diagrams, viva questions and presentation).

## License
Academic project. Add a license (e.g. MIT) before publishing.
