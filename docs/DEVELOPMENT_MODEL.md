# Development Model

**Iterative-incremental** (with agile practices).

**Why:** requirements such as the ML approach depended on findings (whether defensible labels exist); each increment had to be runnable so risks (GitHub limits, schema drift) surfaced early. A pure waterfall would have fixed the ML design before feasibility was known.

| Increment | Phases | Output (verified) |
|---|---|---|
| 1 Foundation | 0–3 | Plan, config, 13-table schema, migration verified on PostgreSQL, FastAPI skeleton |
| 2 Data | 4–5 | GitHub client + collector with pagination/rate limits/normalisation |
| 3 Intelligence | 6–8 | Metric, risk, recommendation engines with unit tests |
| 4 Experience | 9–12 | React dashboard, history, What-If simulator |
| 5 Research | 13–15 | ML experiment with baselines, explanations, PDF report |
| 6 Quality & ops | 16–20 | API/integration/security/migration tests, Docker, CI, deployment config |
| 7 Knowledge | 21–23 | Documentation, diagrams, viva, presentation |

Practices: Git feature branches and PR review, CI on every push, definition of done = code + tests + docs, Dependabot updates.
