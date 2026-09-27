# 11 — Testing and Test Report

## Strategy
| Level | Tool | What |
|---|---|---|
| Unit | pytest | Metric formulas, interpolation, levels, contributions, config validation, recommendation rules, simulator validation, ML features, anomaly detection, model loading |
| API | FastAPI TestClient | Every endpoint: success, validation, not found, conflicts |
| Integration | TestClient + fake GitHub (`httpx.MockTransport`) + real DB | URL → real GitHubClient → collector → engines → PostgreSQL → REST |
| Error | same | Invalid/unavailable repository, 5xx with retries, network failure, rate limit (403 and 429), empty repository, missing data, failed run rollback |
| Security | pytest | Token never in any response or header, settings repr hides token, security headers, CORS, injection-style inputs, no stack traces, no secrets in git or source |
| Migration | Alembic + compare_metadata | Upgrade/downgrade/upgrade and zero schema drift |
| ML | pytest | No temporal leakage, feature values, prediction ↔ explanation consistency, truncated data flag, missing/mismatched model |
| Frontend | Vitest + Testing Library | Formatting, API error parsing, network errors, score strip rendering/accessibility, URL validation, existing-project flow |
| Live end-to-end | `scripts/live_smoke.py` | Real GitHub API against a running server |

**Why a fake GitHub instead of mocks of our own functions?** The fake serves realistic JSON and Link-header pagination through the real HTTP client, so the test exercises the same code that production runs. Only the network is replaced.

## Test report (17 Sep 2026, build environment: Ubuntu 24.04, Python 3.12.3, Node 22.22.2)

| Suite | Result |
|---|---|
| Backend on PostgreSQL 16 (`TEST_DATABASE_URL` set) | **111 passed**, 0 failed |
| Backend on SQLite (default local run) | **111 passed**, 0 failed |
| Backend line coverage | **97%** (CI threshold 85%) |
| `ruff check` | clean |
| Frontend `tsc`, `eslint` | clean |
| Frontend Vitest | **13 passed** |
| Frontend production build | success (initial JS 249 kB, 78 kB gzip) |
| `pip-audit` (runtime requirements), `npm audit` | 0 known vulnerabilities |
| Docker image build / `docker compose up` | **Not executed in the build environment (Docker unavailable)** — runs in CI `docker` job; verify locally |
| Live GitHub smoke test | **partially executed — see below** |

Bugs found by tests during development (and fixed): migration test sharing a database with other tests on PostgreSQL; a security test that could not reach the failing code path; Render-style `postgresql://` URLs not selecting the psycopg driver.

## Live verification (17 Sep 2026)

`scripts/live_smoke.py` was executed against the real GitHub API from the build machine with **no token**. The shared
build IP (35.237.177.196) was rate-limited: `GET https://api.github.com/repos/pallets/click` returned
`HTTP 403` with `x-ratelimit-remaining: 0`, and the whole 60-request hourly quota was consumed by other users of
that IP within seconds of every reset.

**What this verified:** the real GitHub failure path end-to-end — the client detected the quota exhaustion, raised
`RateLimited` with the reset timestamp, and the API returned
`429 {"error": {"code": "GITHUB_RATE_LIMITED", "message": "... Configure GITHUB_TOKEN ...", "reset_at": "..."}}`,
exactly as designed. The backend was running against real PostgreSQL 16 at the time.

**What this did NOT verify:** a complete analysis of a live repository (collection → metrics → risk → report) using
real GitHub data. That path is covered in tests by the fake GitHub server, which reproduces GitHub's payload shapes
and Link-header pagination through the real client code, but it is **not** the same as a live run.

**Action for the team before the demo:** set a personal access token and run

```bash
export GITHUB_TOKEN=<your token>          # restart the backend so it picks the token up
python scripts/live_smoke.py --repo https://github.com/pallets/click \
                             --repo https://github.com/request/request
```
Expected: `run: COMPLETED`, a risk score with factors, recommendations, a 200 simulation and a valid PDF.
Record the output in this document — do not copy numbers that were not produced on your machine.

## Running
```bash
cd backend && pytest                                           # SQLite
TEST_DATABASE_URL=postgresql+psycopg://prospect:pw@localhost:5432/prospect_test \
MIGRATION_TEST_DATABASE_URL=postgresql+psycopg://prospect:pw@localhost:5432/prospect_migrate \
pytest --cov=app                                              # PostgreSQL, as in CI
cd frontend && npm test
python scripts/live_smoke.py --repo https://github.com/pallets/click   # needs running backend
```
