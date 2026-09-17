# 03 — Feasibility Study

## Technical feasibility — feasible
All components use mature open-source technology (FastAPI, SQLAlchemy, PostgreSQL, React, scikit-learn). The GitHub REST API exposes every required entity. **Verified during development:** the backend test suite (110+ tests) passes on PostgreSQL 16; the frontend builds and its tests pass; commit histories of 76 repositories were collected with partial Git clones without using API quota.

**Constraint found:** unauthenticated GitHub access allows 60 requests/hour per IP. During development the shared build machine's quota was exhausted twice by other users. A personal access token (5,000 requests/hour) is required for normal use; the app reports rate limits clearly (HTTP 429 with reset time).

## Economic feasibility — feasible at zero cost
| Item | Cost |
|---|---|
| Software stack | Free, open source |
| GitHub API | Free with personal token |
| Local development | Existing laptops, Docker Desktop (free for education/personal use — check current terms) |
| Hosting (demo) | Free tiers of PaaS providers may suffice; terms change, so verify before deployment |

## Operational feasibility — feasible
Users only paste a repository URL. The dashboard explains every number with tooltips and plain-language explanations. No training beyond the user manual is required.

## Schedule feasibility — feasible for one semester
Iterative-incremental model with 23 phases grouped into 7 milestones (see PROJECT_PLAN.md). Four team members work on parallel tracks (backend, frontend, ML, DB/testing/DevOps).

## Legal and ethical feasibility — feasible with care
Only public data is used, via the official API within its terms. Personal data is minimised (logins only; unlinked authors hashed). The tool assesses *projects*, never individual performance — this is stated in the UI note on the contributors view and in docs/12_SECURITY.md.
