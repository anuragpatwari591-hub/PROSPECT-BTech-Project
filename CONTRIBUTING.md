# Contributing

## Team responsibilities
| Member | Primary ownership | Also reviews |
|---|---|---|
| Anurag Patwari (27) — Project lead | Backend API, orchestration, risk engine, recommendations | ML integration |
| Abhrajit Pal (14) | Frontend, UI/UX, accessibility | API contract (`schemas/api.py`) |
| Pritam Saha (24) | Metric engine, ML experiment, anomaly detection | Risk thresholds |
| Anuska Nayak (22) | Database & migrations, testing, Docker/CI, documentation | Security |

Ownership means first responsibility, not exclusive knowledge: every member must be able to explain the whole system (docs/HOW_IT_WORKS.md, docs/LEARNING_GUIDE.md).

## Git workflow (GitHub Flow with a protected main)
1. `main` is always releasable; protect it (require PR review + green CI).
2. Branch per task: `feature/<short-name>`, `fix/<short-name>`, `docs/<short-name>`.
3. Commit small, meaningful changes using Conventional Commits:
   `feat(risk): add turnaround trend signal` · `fix(collector): skip draft releases` · `test(api): cover 429 path` · `docs(ml): add CI table`.
4. Open a PR, fill in what/why/how tested; at least one teammate reviews.
5. Squash-merge after CI passes; delete the branch.

```bash
git switch main && git pull
git switch -c feature/pr-size-signal
# ...edit, test...
git add -p && git commit -m "feat(metrics): add median PR size"
git push -u origin feature/pr-size-signal     # then open a PR on GitHub
```

## Before opening a PR
- [ ] `cd backend && ruff check . && pytest`
- [ ] `cd frontend && npm run lint && npm run typecheck && npm test`
- [ ] New metric? Definition added and `python scripts/generate_metrics_doc.py` run
- [ ] Model change? `alembic revision --autogenerate` and review the migration
- [ ] No secrets, tokens, `.env` or database dumps in the diff
- [ ] Docs updated if behaviour changed; no unverified claims or results

## Academic integrity
Never fabricate data, results, citations or accuracy. Report negative results. Mark experimental features as experimental.
