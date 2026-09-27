# PROSPECT

**Predictive Software Project Risk & Engineering Control System**

PROSPECT analyzes any public GitHub repository and produces a transparent,
deterministic, rule-based **risk score (0–100)**, a **health score**, a
**LOW / MEDIUM / HIGH / CRITICAL** classification, explainable risk factors,
and actionable recommendations — all from real data pulled live from the
GitHub REST API. No machine learning, no fabricated data, no special-casing
of any repository (including this one).

## Features

1. GitHub repository URL input
2. Real GitHub repository data collection (GitHub REST API)
3. Repository/activity metrics (commit recency, etc.)
4. Issue analysis (open/closed ratio, stale issues)
5. Pull request analysis (merge rate, stale PRs)
6. Contributor dependency analysis ("bus factor")
7. Release analysis (cadence, recency)
8. Transparent rule-based risk score (0–100)
9. Project health score (100 − risk score)
10. LOW / MEDIUM / HIGH / CRITICAL classification
11. Explainable risk factors (every point has a stated reason)
12. Rule-based recommendations
13. Analysis history (persisted in SQLite)
14. What-If risk simulator (hypothetical metrics, instant re-scoring)
15. Professional web dashboard
16. PDF report generation
17. Automated backend test suite (pytest)
18. One-click Windows launcher (`start.bat`)
19. Full documentation (this file + `docs/`)

See `docs/RISK_ALGORITHM.md` for the exact scoring rules and
`docs/ARCHITECTURE.md` for how the system fits together.

## Tech stack

```
React + Vite + JavaScript + CSS      (frontend/)
        |
Python + FastAPI REST API            (backend/)
        |
SQLite                                (backend/prospect.db)
        |
GitHub REST API                       (https://api.github.com)
```

Deliberately simple: no Kubernetes, no message queues, no NoSQL clusters, no
ML/MLOps frameworks. Every part of this stack can be explained end-to-end in
a viva.

## Project structure

```
prospect-software-risk-analyzer/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, startup
│   │   ├── config.py         # env-driven configuration
│   │   ├── database.py       # SQLAlchemy engine/session
│   │   ├── models.py         # Analysis table
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── github_client.py  # real GitHub REST API client
│   │   ├── risk_engine.py    # deterministic risk scoring engine
│   │   ├── pdf_report.py     # PDF report generation (ReportLab)
│   │   └── routers/          # analyze / history / whatif / report
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/       # RepoInput, Dashboard, WhatIfSimulator, ...
│   │   ├── api.js            # fetch wrapper for the backend API
│   │   ├── App.jsx
│   │   └── styles/index.css
│   ├── package.json
│   └── vite.config.js
├── tests/                    # pytest suite (runs against backend/app)
│   ├── conftest.py
│   ├── test_risk_engine.py
│   ├── test_github_client.py
│   └── test_api.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── RISK_ALGORITHM.md
├── start.bat                 # one-click Windows setup + launch
├── requirements.txt          # convenience pointer to backend/requirements.txt
├── package.json              # convenience npm scripts that delegate to frontend/
├── pytest.ini
└── README.md
```

## Windows setup (recommended path)

**Prerequisites:** [Python 3.10+](https://www.python.org/downloads/) and
[Node.js 18+](https://nodejs.org/) installed and available on `PATH`.

1. Download or `git clone` this repository.
2. Double-click **`start.bat`** (or run it from a terminal:
   `start.bat`).
3. The script will:
   - Create a Python virtual environment in `backend/venv` and install
     backend dependencies.
   - Install frontend dependencies with `npm install` (first run only).
   - Launch the backend API in one window (`http://127.0.0.1:8000`).
   - Launch the frontend dev server in another window
     (`http://127.0.0.1:5173`).
   - Open the app in your default browser automatically.
4. To stop, close the two opened terminal windows.

## Manual setup (Windows / macOS / Linux)

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is now live at `http://127.0.0.1:8000` (interactive docs at
`http://127.0.0.1:8000/docs`).

Optional: copy `backend/.env.example` to `backend/.env` and set
`GITHUB_TOKEN` to a personal access token to raise the GitHub API rate
limit from 60 to 5,000 requests/hour. No scopes are required for public
repositories.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` in your browser. The Vite dev server proxies
`/api/*` requests to the backend on port 8000 (see `vite.config.js`), so no
CORS configuration is needed for local development.

## Running the tests

```bash
# with the backend virtual environment activated (see backend setup above):
pytest -v
```

Run this from the repository root — `pytest.ini` points pytest at the
`tests/` directory, and `tests/conftest.py` adds `backend/` to the import
path so the tests can `import app...` without installing it as a package.

The suite covers:
- The risk engine's scoring rules in isolation (no network calls).
- The GitHub client's URL parsing and response normalization, including
  edge cases like empty repositories.
- The full FastAPI request/response cycle for `/api/analyze`,
  `/api/history`, `/api/whatif/{id}`, and `/api/report/{id}` with the
  GitHub API mocked out (so tests are fast and don't hit rate limits).

## API reference

| Method | Path | Description |
|---|---|---|
| `GET`  | `/api/health` | Liveness check |
| `POST` | `/api/analyze` | Analyze a GitHub repo (`{"repo_url": "..."}`) and store the result |
| `GET`  | `/api/history` | List past analyses (most recent first) |
| `GET`  | `/api/history/{id}` | Get one full stored analysis |
| `DELETE` | `/api/history/{id}` | Delete a stored analysis |
| `POST` | `/api/whatif/{id}` | Re-run the risk engine with hypothetical metric overrides |
| `GET`  | `/api/report/{id}` | Download a PDF report for a stored analysis |

Full interactive documentation is auto-generated by FastAPI at `/docs` while
the backend is running.

## How the risk score works (summary)

The engine scores five independent categories that always sum to 100
points of maximum risk:

| Category | Max points |
|---|---|
| Repository Activity | 25 |
| Issue Management | 20 |
| Pull Request Health | 15 |
| Contributor Dependency (Bus Factor) | 25 |
| Release Cadence | 15 |

Risk Score = sum of category points. Health Score = 100 − Risk Score.
Classification: 0–25 LOW, 26–50 MEDIUM, 51–75 HIGH, 76–100 CRITICAL.

The exact thresholds, formulas, and rationale are documented in full in
[`docs/RISK_ALGORITHM.md`](docs/RISK_ALGORITHM.md). The algorithm is
identical for every repository — it only ever looks at metrics, never at a
repository's name or owner, so it cannot be biased toward or against any
specific project.

## Notes on GitHub API usage

- Works without any credentials (60 requests/hour, shared across all
  unauthenticated traffic from your IP).
- Set `GITHUB_TOKEN` in `backend/.env` for 5,000 requests/hour.
- Only real GitHub API responses are used. If a repository has no releases,
  no pull requests, etc., that is reported as zero/empty — nothing is ever
  invented.
