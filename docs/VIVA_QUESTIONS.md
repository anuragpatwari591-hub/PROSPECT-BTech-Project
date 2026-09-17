# Viva Questions

57 questions. Format: **Q** · *Simple answer* · Technical answer · ↪ Possible follow-up.

## Motivation

**1. Why did you build PROSPECT?**

- *Simple:* Project trouble shows up in development activity before it becomes obvious; we wanted an explainable early-warning tool.
- *Technical:* GitHub exposes commits, issues, PRs and releases via API; we convert them into documented metrics and an additive risk model whose contributions explain the score.
- ↪ *Follow-up:* Who would actually use it?

## Problem

**2. What problem does it solve that GitHub Insights does not?**

- *Simple:* Insights shows charts; PROSPECT interprets them, explains a score, and recommends actions.
- *Technical:* Adds normalisation, 22 defined metrics, weighted multi-dimension scoring with exact attribution, factor-linked rules, simulation, history and reports.
- ↪ *Follow-up:* Isn't a single score an oversimplification?

**3. Is a single score an oversimplification?**

- *Simple:* Yes if shown alone, so we always show where the points come from.
- *Technical:* The score decomposes into 13 signal contributions; the UI shows dimensions and factors with metric values; coverage shows how much of the model had data.
- ↪ *Follow-up:* What does coverage 85% mean?

## Research gap

**4. What is your research gap?**

- *Simple:* Pieces exist separately; an open, explainable, integrated tool combining them is what we built.
- *Technical:* Integration of documented metrics + additive attribution + linked recommendations + what-if on the same model + leakage-controlled ML with baselines. No new algorithm is claimed.
- ↪ *Follow-up:* Name related work.

**5. Name three related papers.**

- *Simple:* Truck factors, why projects fail, and pull-request studies.
- *Technical:* Avelino et al. ICPC 2016 (truck factor, 133 repos); Coelho & Valente FSE 2017 (104 deprecated projects, nine reasons); Gousios et al. ICSE 2014 (pull-based development). Also Coelho et al. ESEM 2018 on unmaintained projects.
- ↪ *Follow-up:* How does your bus factor differ from Avelino's?

## Architecture

**6. Explain your architecture.**

- *Simple:* React frontend, FastAPI backend, PostgreSQL database, GitHub as external source.
- *Technical:* Layered: routes → services (collector, orchestrator, report) → pure engines (metrics, risk, recommendations, simulator, ML) → SQLAlchemy/PostgreSQL; GitHub client isolated behind an interface.
- ↪ *Follow-up:* Why separate engines from services?

**7. Why keep engines as pure functions?**

- *Simple:* They are easy to test and reason about.
- *Technical:* No I/O: given metrics and config, output is deterministic; unit tests use hand-computed values; the simulator reuses the same engine safely.
- ↪ *Follow-up:* Where does I/O happen then?

**8. Why is analysis asynchronous?**

- *Simple:* Collection can take long; the user shouldn't wait on one HTTP request.
- *Technical:* POST returns 202 with a run id; FastAPI BackgroundTasks runs execute_run with its own session; UI polls run status every 2 s.
- ↪ *Follow-up:* What happens if the server restarts mid-run?

**9. What if the server restarts during analysis?**

- *Simple:* That run never finishes, so we mark it failed later.
- *Technical:* Runs older than 15 minutes in PENDING/RUNNING are set FAILED with STALE_RUN when a new analysis is requested. A task queue would be the production improvement.
- ↪ *Follow-up:* Why not Celery?

## GitHub API

**10. How do you handle pagination?**

- *Simple:* We follow GitHub's 'next page' links.
- *Technical:* per_page=100; parse the Link header rel=next; stop at MAX_PAGES_PER_ENDPOINT; mark truncated; for PRs stop early when updated_at is older than the window.
- ↪ *Follow-up:* What does truncation do to metrics?

**11. How do you handle rate limits?**

- *Simple:* We detect them and tell the user when to retry; a token raises the limit.
- *Technical:* 403/429 with x-ratelimit-remaining 0 → RateLimited with reset_at → API 429 GITHUB_RATE_LIMITED; cache TTL and page caps reduce calls. 60/h unauthenticated vs 5,000/h with token.
- ↪ *Follow-up:* Did this happen during development?

**12. Why is the issues endpoint tricky?**

- *Simple:* GitHub counts pull requests as issues.
- *Technical:* Items containing a pull_request key are removed during normalisation; tested with a fake PR #999.
- ↪ *Follow-up:* What other normalisation do you do?

**13. How is the GitHub token protected?**

- *Simple:* It stays on the server and is never sent to the browser.
- *Technical:* Env var → pydantic SecretStr → Authorization header only; health endpoint returns a boolean; test scans every response (incl. PDF and OpenAPI) for the token.
- ↪ *Follow-up:* What if someone commits .env?

## Database

**14. Why PostgreSQL?**

- *Simple:* Reliable, free, supports constraints and JSON.
- *Technical:* ACID transactions for rollback on failed collection; CHECK/UNIQUE/FK cascade constraints; composite indexes; widely hosted.
- ↪ *Follow-up:* Why not MongoDB?

**15. Why store raw GitHub data instead of only results?**

- *Simple:* So we can recompute and cache without new API calls.
- *Technical:* Raw entities upserted by natural keys; per-run derived tables preserve exact history; charts query stored commits/issues/PRs.
- ↪ *Follow-up:* How do you avoid duplicates?

**16. How do you avoid duplicate rows?**

- *Simple:* Unique constraints plus update-if-exists.
- *Technical:* UNIQUE(project_id, sha/number/github_id); _upsert loads existing keys then inserts or updates within one transaction.
- ↪ *Follow-up:* Why not ON CONFLICT?

**17. What is Alembic used for and how did you verify it?**

- *Simple:* Versioned database schema changes.
- *Technical:* Revision 0001 generated from models; test runs upgrade/downgrade/upgrade and compare_metadata must be empty, on PostgreSQL in CI.
- ↪ *Follow-up:* What happens when you add a column?

**18. What personal data do you store?**

- *Simple:* Only public GitHub usernames.
- *Technical:* Unlinked commit authors become 'unlinked-' + 8 hex chars of salted SHA-256 of the e-mail; no names, e-mails or IPs.
- ↪ *Follow-up:* Is a hash truly anonymous?

## Metrics

**19. Define activity trend.**

- *Simple:* How much the last month's commit rate changed compared to the two months before.
- *Technical:* (c30 − c60/2)/(c60/2)×100, capped ±100; null if both zero; +100 if baseline zero.
- ↪ *Follow-up:* Why cap it?

**20. Define the commit-share bus factor.**

- *Simple:* The fewest people who made half of recent commits.
- *Technical:* min k such that top-k authors' commits ≥ 50% of non-bot commits in 90 days. Simplified; not the file-authorship algorithm of Avelino et al.
- ↪ *Follow-up:* What are its weaknesses?

**21. Why use medians for PR turnaround?**

- *Simple:* A few very slow PRs would distort an average.
- *Technical:* Turnaround distributions are right-skewed; median is robust to outliers.
- ↪ *Follow-up:* What does turnaround exclude?

**22. How did you make sure metrics are not invented formulas?**

- *Simple:* Each is a simple, standard count, ratio or median with written limitations.
- *Technical:* METRIC_DEFINITIONS holds definition, formula, source, unit, interpretation, limitations; docs generated from code; unit tests with hand-calculated values.
- ↪ *Follow-up:* Give a limitation of issue close ratio.

**23. How do you handle missing data?**

- *Simple:* We show 'not available' instead of guessing.
- *Technical:* Metric returns None + note; risk engine skips the signal (except recency, where no commits is itself evidence); dimensions without data are excluded and weights renormalised.
- ↪ *Follow-up:* Why is recency treated differently?

## Risk calculation

**24. How is the risk score calculated?**

- *Simple:* Each factor gets 0–100, factors are averaged per area, areas are weighted and added.
- *Technical:* Piecewise-linear interpolation per signal → dimension mean → Σ w'·score with weights renormalised over applicable dimensions; levels at 25/50/75.
- ↪ *Follow-up:* Work an example.

**25. Work a numeric example of one contribution.**

- *Simple:* Slow PR reviews add some points to the score.
- *Technical:* Turnaround 9 days on points (1,0),(4,50),(14,100) → 75. PR dimension has 4 signals; if releases are N/A, weight 0.20/0.85 = 0.235; contribution = 0.235×75/4 ≈ 4.4 points.
- ↪ *Follow-up:* Do all contributions sum to the score?

**26. Why are the weights 0.25/0.20/0.20/0.20/0.15?**

- *Simple:* They reflect our judgement that activity is the broadest signal.
- *Technical:* Heuristic defaults, configurable via RISK_CONFIG_PATH, validated on load, snapshot stored per run. Not calibrated on outcomes — stated in UI and report.
- ↪ *Follow-up:* How would you validate them?

**27. Is your risk score scientifically validated?**

- *Simple:* No, and we say so clearly.
- *Technical:* No labelled risk outcomes were available; the UI disclaimer and docs/06 state it is heuristic; future work proposes validation with maintainer judgements.
- ↪ *Follow-up:* Then why is it useful?

**28. What does coverage mean?**

- *Simple:* How much of the model had data to work with.
- *Technical:* Sum of weights of applicable dimensions ÷ total weight; e.g. 0.85 when the project has no GitHub Releases.
- ↪ *Follow-up:* Is a project without releases penalised?

## ML

**29. Why didn't you train ML to predict the risk score?**

- *Simple:* There is no real 'risk' label; we'd just be copying our own rules.
- *Technical:* Training on rule-derived labels only reproduces the rules; fabricating labels would be dishonest. We chose an observable outcome instead.
- ↪ *Follow-up:* What outcome?

## Dataset

**30. What dataset did you use for ML?**

- *Simple:* Commit histories of 76 public GitHub repositories.
- *Technical:* Partial git clones (commits only); cutoffs every 90 days; 3,533 samples; 2.5% positives; hand-picked convenience sample (selection bias documented).
- ↪ *Follow-up:* Why not use the GitHub API?

**31. How is the ML label defined?**

- *Simple:* Whether an active project has no commits in the next six months.
- *Technical:* label = 1 if zero non-bot commits in (T, T+180d], for repos with ≥1 commit in the 90 days before T; last T ≤ collection date − 180d.
- ↪ *Follow-up:* Why require recent activity?

## Feature engineering

**32. Which features did you use and why?**

- *Simple:* Recent commit counts, regularity, recency, trend, and team size/concentration.
- *Technical:* log commits 30/90/180d, active-week share 26w, days since last commit, smoothed 30-vs-180-day rate ratio, authors 90d, top author share 180d; log transforms reduce skew.
- ↪ *Follow-up:* Why log transform?

## Data leakage

**33. How did you prevent data leakage?**

- *Simple:* Features use only the past; labels only the future; repositories never appear in both train and test.
- *Technical:* commit_features filters ≤ T (unit tested); GroupShuffleSplit by repo with disjointness assertion; GroupKFold for selection; same feature code for serving.
- ↪ *Follow-up:* What leakage would a random split cause?

**34. What would go wrong with a random row split?**

- *Simple:* The model would see almost the same data in training and testing.
- *Technical:* Successive cutoffs of one repository are highly correlated; random splits let the model memorise repositories, inflating scores.
- ↪ *Follow-up:* Did you check temporal drift?

## Model evaluation

**35. Your accuracy is 91.5% — is that good?**

- *Simple:* No — accuracy is misleading here.
- *Technical:* Only 1.9% of test samples are positive; always predicting 'not dormant' gives 98.1% accuracy. We report balanced accuracy, precision, recall, F1, ROC-AUC, PR-AUC.
- ↪ *Follow-up:* Which metric matters most?

**36. What were your actual results?**

- *Simple:* The model ranks well but doesn't clearly beat a simple rule.
- *Technical:* LR test: ROC-AUC 0.950 [0.907–0.981], PR-AUC 0.379 [0.189–0.639], precision 0.16, recall 0.81. Rule (>60 days): ROC-AUC 0.908, PR-AUC 0.239 [0.142–0.445], F1 0.40 (best).
- ↪ *Follow-up:* Why serve the model at all?

**37. How did you compute confidence intervals?**

- *Simple:* By resampling test repositories many times.
- *Technical:* Cluster bootstrap: 1,000 resamples of the 16 test repositories with replacement; 2.5/97.5 percentiles of ROC-AUC and PR-AUC.
- ↪ *Follow-up:* Why resample repositories not rows?

**38. How did you handle class imbalance?**

- *Simple:* We weighted the rare class more and used imbalance-aware metrics.
- *Technical:* class_weight='balanced'; PR-AUC and balanced accuracy; no oversampling to avoid synthetic data.
- ↪ *Follow-up:* What about threshold tuning?

## Explainability

**39. How do you explain the risk score?**

- *Simple:* Every point is traced to a factor with its value and threshold.
- *Technical:* Additive model → exact per-signal contributions; explanation strings state value, zero-risk and max-risk points and signal score.
- ↪ *Follow-up:* How is this different from SHAP?

**40. Why didn't you use SHAP?**

- *Simple:* Our models are linear, so exact explanations are simpler.
- *Technical:* For standardised logistic regression, contribution = coef × z in log-odds — exact; SHAP adds a heavy dependency without extra fidelity; appropriate for tree/black-box models.
- ↪ *Follow-up:* Can coefficients be trusted?

**41. Can the logistic regression coefficients be interpreted causally?**

- *Simple:* No.
- *Technical:* Features are correlated (30/90/180-day counts), so coefficients are unstable; UI warns of this (cf. Jiarpakdee et al., TSE 2019).
- ↪ *Follow-up:* How would you reduce multicollinearity?

## ML

**42. What does the anomaly detector do?**

- *Simple:* Finds unusual weeks compared to the project's own history.
- *Technical:* Isolation Forest on 52 weekly vectors, reported only if a feature is ≥3 robust z-scores away; needs ≥12 active weeks; not part of the score; no accuracy claimed.
- ↪ *Follow-up:* Why the z-score filter?

## What-If

**43. How does the What-If simulator work?**

- *Simple:* It reruns the same risk calculation with the numbers you change.
- *Technical:* Whitelisted metrics with ranges; baseline and simulated compute_risk; returns scores, levels, difference and dimension scores; stores a Scenario; labelled SIMULATION / ESTIMATE.
- ↪ *Follow-up:* Why isn't it a prediction?

**44. Why is the simulation not a prediction?**

- *Simple:* Real changes affect several metrics at once and the model isn't validated.
- *Technical:* It shows model sensitivity under hypothetical inputs, holding others constant; causality and future behaviour are not modelled.
- ↪ *Follow-up:* Why can't users simulate open issue count?

## Recommendations

**45. How are recommendations generated?**

- *Simple:* Each strong risk factor has a matching piece of advice.
- *Technical:* Rule per signal; fires when score ≥ 50, HIGH priority if ≥ 75; stored with risk_factor_id; test ensures every signal has a rule.
- ↪ *Follow-up:* Are recommendations proven to reduce risk?

## Security

**46. What security measures did you implement?**

- *Simple:* Secret protection, validation, safe errors, headers, and audit logs.
- *Technical:* SecretStr token; regex + Pydantic validation; ORM bound params; CORS allow-list; nosniff/DENY/CSP/HSTS; generic 500; non-root container; dependency audits; tests for each.
- ↪ *Follow-up:* Why no login?

**47. Why no authentication?**

- *Simple:* All data is public and it's a single-team tool, so login added risk without value for v1.
- *Technical:* Documented decision with consequences and a migration path (hashed passwords, JWT in HttpOnly cookies, ownership checks); deploy privately meanwhile.
- ↪ *Follow-up:* What's the main risk of no auth?

**48. How do you prevent SQL injection?**

- *Simple:* We never build SQL strings from user input.
- *Technical:* SQLAlchemy parameter binding; typed ids; URL regex; tests send injection payloads and confirm 422 and table integrity.
- ↪ *Follow-up:* What about XSS in the PDF?

## Testing

**49. How did you test the GitHub integration without calling GitHub?**

- *Simple:* A fake GitHub server inside the tests.
- *Technical:* httpx.MockTransport serving realistic JSON and Link pagination, exercising the real client, collector and DB; plus a live smoke script against the real API.
- ↪ *Follow-up:* What error cases are covered?

**50. What test results do you have?**

- *Simple:* All tests pass with high coverage.
- *Technical:* 111 backend tests pass on PostgreSQL 16 and SQLite, 97% coverage; 13 frontend tests; lint/typecheck clean; pip-audit/npm audit clean.
- ↪ *Follow-up:* What isn't tested?

## Docker

**51. What does docker compose up start?**

- *Simple:* Database, backend and frontend together.
- *Technical:* postgres:16 with health check and volume; backend image migrates then runs uvicorn as non-root; nginx serves the SPA and proxies /api; DB not exposed to host.
- ↪ *Follow-up:* Why a multi-stage frontend build?

## CI/CD

**52. What does your CI pipeline do?**

- *Simple:* Checks every push automatically.
- *Technical:* GitHub Actions: backend lint + tests on PostgreSQL service with coverage gate; frontend lint/typecheck/test/build; Docker image builds and compose validation. No auto-deploy yet.
- ↪ *Follow-up:* Why no automatic deployment?

## Deployment

**53. How would you deploy it?**

- *Simple:* With a Render Blueprint or any Docker host.
- *Technical:* render.yaml provisions managed PostgreSQL, Docker API with /api/health, static frontend; secrets set in dashboard; DB URL normalised to psycopg.
- ↪ *Follow-up:* What environment variables are required?

## Limitations

**54. What are the main limitations?**

- *Simple:* The score isn't validated and GitHub shows only part of a project.
- *Technical:* Heuristic thresholds; public GitHub data only; commit counts as proxy; page caps; ML convenience sample with 16 test positives; no auth; background tasks in-process.
- ↪ *Follow-up:* Which limitation matters most?

## Future scope

**55. What would you do next?**

- *Simple:* Validate the score and improve the ML study.
- *Technical:* Maintainer-judgement or outcome-based calibration; larger random samples; file-authorship truck factor; scheduled analyses; OAuth for private repos.
- ↪ *Follow-up:* How would you validate the score?

## Ethics

**56. Could PROSPECT be misused?**

- *Simple:* Yes, to judge individual developers, which we warn against.
- *Technical:* Commit counts ignore reviews/mentoring/design; UI notes projects not people; no personal data beyond logins; disclaimers on scores.
- ↪ *Follow-up:* What SDG does it support?

## Process

**57. Which development model did you follow?**

- *Simple:* Iterative and incremental.
- *Technical:* 23 phases in 7 milestones; each increment runnable and tested; CI on every change; feature branches with PR review.
- ↪ *Follow-up:* How did you divide work?
