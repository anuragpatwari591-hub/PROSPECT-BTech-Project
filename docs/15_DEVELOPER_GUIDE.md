# 15 — Developer Guide

## Setup
See docs/13_DEPLOYMENT.md §B. Python 3.12, Node 22, PostgreSQL 16 (or SQLite for quick tests).

## Everyday commands
| Task | Command |
|---|---|
| Backend dev server | `cd backend && uvicorn app.main:app --reload` |
| Backend tests | `pytest` (SQLite) or with `TEST_DATABASE_URL` (PostgreSQL) |
| Lint / autofix | `ruff check . --fix` |
| New migration | `alembic revision --autogenerate -m "..."` then review the file |
| Frontend dev | `cd frontend && npm run dev` |
| Frontend checks | `npm run lint && npm run typecheck && npm test && npm run build` |
| Regenerate metrics doc | `python scripts/generate_metrics_doc.py` |
| Re-run ML experiment | `python ml/collect_histories.py && python ml/train_dormancy.py` |
| Live smoke test | `python scripts/live_smoke.py --repo https://github.com/pallets/click` |

## How to add a metric
1. Add its definition to `METRIC_DEFINITIONS` and compute it in `compute_metrics` (`engines/metrics.py`).
2. Add a unit test in `tests/test_metrics.py` with hand-calculated expected values.
3. Run `scripts/generate_metrics_doc.py`.
4. (Optional) Use it in a signal: add to `risk_config.py`, add a rule in `recommendations.py`, add it to `SIMULATABLE_METRICS` and to `METRIC_LABELS` in `frontend/src/lib/format.ts`. Tests enforce that every signal has a rule and every signal metric is simulatable.

## How to change weights/thresholds
Edit a JSON copy of the default config and set `RISK_CONFIG_PATH`. Document the reason in docs/06_RISK_MODEL.md. Old runs keep their stored config snapshot.

## Conventions
- Engines stay pure (no DB/network). Services orchestrate. Routes validate and translate errors.
- Errors: raise `APIError(status, CODE, message)` or a `GitHubError` subclass.
- Never log or return secrets. Never guess missing data — return `None` with a note.
- Frontend: typed API responses in `lib/types.ts`; every data view has loading, empty and error states.
