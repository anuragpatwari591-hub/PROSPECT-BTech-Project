# PROSPECT Architecture

```
┌─────────────────────┐        HTTPS         ┌──────────────────────┐
│   React + Vite SPA  │  ───────────────────▶ │   FastAPI REST API   │
│   (frontend/)        │  ◀─────────────────── │   (backend/app/)      │
└─────────────────────┘        JSON           └──────────┬───────────┘
                                                            │
                                              ┌─────────────┼─────────────┐
                                              │                           │
                                       ┌──────▼──────┐           ┌────────▼────────┐
                                       │   SQLite     │           │  GitHub REST API │
                                       │ (analysis     │           │  api.github.com  │
                                       │  history)     │           └─────────────────┘
                                       └──────────────┘
```

## Layers

### Frontend — `frontend/`
Plain React (via Vite) + JavaScript + CSS. No UI framework, no state
management library — `useState`/`useEffect` and a small `fetch` wrapper
(`src/api.js`) are enough for this app's scope.

Key components (`src/components/`):
- `RepoInput` — GitHub URL entry.
- `Dashboard` — composes everything below for one analysis result.
- `RiskScoreCard` — the big score, health score, classification badge.
- `RiskFactorsPanel` — per-category breakdown with explanations.
- `MetricsPanel` — raw repository metrics grid.
- `RecommendationsPanel` — rule-triggered recommendations.
- `WhatIfSimulator` — sliders that re-run the risk engine hypothetically.
- `HistoryPanel` — past analyses, stored server-side in SQLite.

During development, Vite proxies `/api/*` to the FastAPI server
(`vite.config.js`), so the browser only ever talks to one origin.

### Backend — `backend/app/`
FastAPI application, organized by responsibility:

- `github_client.py` — talks to the real GitHub REST API only. Parses
  repository URLs, paginates commits/issues/PRs/releases/contributors, and
  normalizes the response into a `RepoMetrics` object. Never fabricates
  data — GitHub's absence of data (e.g. no releases) becomes zero/`None`.
- `risk_engine.py` — pure, deterministic scoring functions. Takes a
  `RepoMetrics` in, returns a `RiskResult` out. Has no network or database
  dependency, which is what makes it trivial to unit test and reuse for the
  What-If simulator.
- `models.py` / `database.py` — SQLAlchemy models and session management
  for the SQLite-backed `analyses` table (analysis history).
- `schemas.py` — Pydantic request/response contracts.
- `pdf_report.py` — renders a stored analysis into a PDF using ReportLab.
- `routers/` — one FastAPI router per concern: `analyze`, `history`,
  `whatif`, `report`.

### Data store — SQLite
A single `prospect.db` file (`backend/prospect.db`, git-ignored) stores
every completed analysis: the repo's identity, its risk/health scores, the
full breakdown of factors, recommendations, and the raw metrics snapshot
(as JSON) that the What-If simulator replays against. SQLite was chosen
deliberately: no separate database server to install or configure, which
keeps the project's operational footprint appropriate for a B.Tech project
and a Windows `start.bat` launch.

### External dependency — GitHub REST API
The only external service PROSPECT talks to. Works unauthenticated (60
requests/hour) or with a personal access token set as `GITHUB_TOKEN` for a
much higher rate limit — see the README.

## Request flow: analyzing a repository

1. User submits a GitHub URL in the React app.
2. Frontend calls `POST /api/analyze`.
3. `github_client.parse_repo_url` extracts `owner/repo`.
4. `github_client.build_metrics` fetches repo info, commits, contributors,
   issues, pull requests, and releases from the real GitHub API.
5. `risk_engine.calculate_risk` scores the resulting `RepoMetrics`.
6. The result is persisted to SQLite (`Analysis` row) and returned as JSON.
7. The frontend renders the dashboard from that JSON.

## Request flow: What-If simulation

1. User drags sliders in `WhatIfSimulator`.
2. Frontend calls `POST /api/whatif/{analysis_id}` with only the overridden
   fields.
3. The backend loads the *stored* metrics for that analysis, merges in the
   overrides, and calls `risk_engine.calculate_risk` again — no GitHub call.
4. The simulated result is returned (and never persisted), so the original
   analysis in history is untouched.

## Why this stack

The brief called for a simple, B.Tech-defensible stack: React for a
familiar, well-documented UI layer; FastAPI for a modern, typed, easy-to-
explain Python API; SQLite for zero-ops persistence; and the GitHub REST
API as the single source of truth for repository data. No queues, no
container orchestration, no ML frameworks — every moving part here can be
explained on a whiteboard in one pass.
