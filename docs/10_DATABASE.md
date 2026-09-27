# 10 — Database Design

PostgreSQL 16, accessed through SQLAlchemy 2.0; schema versioned with Alembic (`backend/alembic/versions/0001_initial_schema.py`). Migrations are tested: upgrade → downgrade → upgrade, then Alembic's `compare_metadata` must report **no difference** from the ORM models (`tests/test_migrations.py`).

ER diagram: [docs/ER_DIAGRAM.md](ER_DIAGRAM.md).

## Tables
| Table | Purpose | Key constraints / indexes |
|---|---|---|
| projects | Registered repository and metadata | UNIQUE(owner, repo) |
| commits | Normalised commits (author key, bot flag, time) | UNIQUE(project_id, sha); INDEX(project_id, authored_at) |
| issues | Issues without PRs | UNIQUE(project_id, number); CHECK state; INDEX(project_id, state) |
| pull_requests | PRs with optional size | UNIQUE(project_id, number); CHECK state |
| releases | Non-draft releases | UNIQUE(project_id, github_id) |
| contributors | All-time contribution counts | UNIQUE(project_id, login) |
| analysis_runs | One analysis execution | CHECK status; INDEX(project_id, started_at) |
| repository_metrics | Metric value per run | UNIQUE(run_id, key) |
| risk_assessments | Score, level, coverage, config snapshot, dimension breakdown | UNIQUE(run_id); CHECK 0 ≤ score ≤ 100; CHECK level |
| risk_factors | One row per signal | INDEX(assessment_id) |
| recommendations | Advice linked to factor | FK risk_factor_id ON DELETE SET NULL |
| scenarios | Saved What-If simulations | INDEX(project_id) |
| audit_logs | project_created, project_deleted, analysis_requested, report_generated | INDEX(action), INDEX(created_at) |

All foreign keys to a project or run use `ON DELETE CASCADE` at the database level **and** ORM cascades, so deleting a project removes everything derived from it.

## Normalisation
Raw entities are in 3NF keyed by (project_id, natural GitHub key). Derived results reference the run that produced them. JSON columns are used only for data that is read as a whole and never queried by field: collection notes, ML output, configuration snapshot, per-dimension breakdown, scenario overrides, audit details.

## Why store raw data at all?
It enables re-computation without API calls (cache), weekly activity charts, contributor views, and future re-scoring with a new configuration.

## Personal data
Only GitHub logins (already public) are stored. Commit e-mails are converted to `unlinked-<8-hex>` salted SHA-256 prefixes. No IP addresses are logged in audit_logs.

## Commands
```bash
cd backend
alembic upgrade head                                  # apply migrations
alembic revision --autogenerate -m "describe change"  # after editing models
alembic downgrade -1                                  # roll back one revision
```
