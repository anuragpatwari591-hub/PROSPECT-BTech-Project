# PROSPECT — Presentation (14 slides)

Speaker notes are in *italics*. Never present a number that you did not produce yourself.

---
## Slide 1 — Title
**PROSPECT**
Predictive Software Project Risk Analysis and Decision Support System
Anurag Patwari (27) · Abhrajit Pal (14) · Pritam Saha (24) · Anuska Nayak (22)
Third-year B.Tech Software Engineering project
*One line: "We built a tool that reads a GitHub repository's development activity and explains where the project is at risk."*

---
## Slide 2 — Problem
- Projects rarely fail suddenly — activity slows, backlogs grow, reviews stall, knowledge concentrates
- These traces are public on GitHub, but teams judge projects by stars or "last commit" date
- A score nobody can explain cannot be acted on
*Ask the audience: "How would you decide today whether a library you depend on is still healthy?"*

---
## Slide 3 — Motivation
- Student teams get no objective feedback on their engineering process
- Developers pick dependencies with little evidence about maintenance
- Maintainers notice contributor concentration only when the key person leaves
- Public API + documented metrics + a transparent model = decision support that can be checked

---
## Slide 4 — Existing systems
| Tool | What it gives | What is missing |
|---|---|---|
| GitHub Insights | Raw charts | No interpretation, no score, no advice |
| Repository badges | Single facts (build, coverage) | No project-level risk view |
| Research prototypes | Strong methods (truck factor, failure studies) | Not an integrated, usable tool |
| Commercial analytics | Dashboards | Closed scoring, not explainable or free |

---
## Slide 5 — Research gap (conservative)
- Studied: mining GitHub (Kalliamvakou et al., MSR 2014), pull-based development (Gousios et al., ICSE 2014), truck factor (Avelino et al., ICPC 2016), project failure (Coelho & Valente, FSE 2017), unmaintained projects (Coelho et al., ESEM 2018), XAI for SE (Tantithamthavorn et al.)
- **We claim no new algorithm.** Prediction of maintenance decline already exists.
- Gap we address: an **open, integrated, explainable** tool — documented metrics + exact attribution + linked recommendations + What-If on the same model + an ML experiment with leakage control and honest baselines

---
## Slide 6 — Proposed system
Paste a repository URL →
collect commits, issues, PRs, contributors, releases →
22 documented metrics →
risk score 0–100 with per-factor contributions →
recommendations tied to factors →
What-If simulation · history · PDF report
*Emphasise: every point of the score is traceable.*

---
## Slide 7 — Architecture
React + TypeScript SPA → FastAPI → PostgreSQL, with GitHub as the external source
- Pure engines (metrics, risk, recommendations, simulator) — no I/O, fully unit-tested
- Services handle collection, orchestration, reporting; analysis runs as a background task (202 + polling)
- Docker Compose: nginx (SPA + /api proxy), backend (non-root, migrates on start), PostgreSQL
*Show docs/diagrams/UML.md component and deployment diagrams.*

---
## Slide 8 — Methodology
1. Validate URL → confirm repository exists
2. Collect with pagination, retries, rate-limit handling, 30-minute cache, page caps
3. Normalise: drop PRs from issues, flag bots, hash authors without accounts (no e-mails stored)
4. Store raw data once, compute per run (exact history, no re-fetch)
5. Metrics → risk → recommendations → experimental ML
6. Present: dashboard, simulator, history, PDF
*Development model: iterative-incremental, 23 phases, 7 milestones, CI on every push.*

---
## Slide 9 — Metrics
- 22 metrics, each with definition, formula, data source, unit, interpretation, **limitations**
- Documentation is generated from the code, so it cannot drift
- Examples: activity trend `(c30 − c60/2)/(c60/2)×100`; median PR turnaround; stale open PR ratio; top-contributor share; commit-share bus factor = fewest authors making ≥ 50% of 90-day commits
- Missing data returns "not available" with a reason — never a guessed value

---
## Slide 10 — Risk model
```
Risk = Σ (renormalised weight × dimension score)
Activity .25 | Issues .20 | Pull requests .20 | Contributors .20 | Releases .15
LOW < 25 ≤ MEDIUM < 50 ≤ HIGH < 75 ≤ CRITICAL       Health = 100 − Risk
```
- Each signal: metric → 0–100 by piecewise-linear interpolation between configured thresholds
- Contributions of all signals **sum exactly to the score** → the explanation is the calculation
- Dimensions without data are excluded and weights rescaled ("coverage")
- **Thresholds are our heuristics, not validated** — stated in the UI and the report

---
## Slide 11 — Machine learning (experimental)
- No public "risky project" labels exist → we refused to invent one
- Instead: predict an observable outcome — zero non-bot commits in the next 180 days for a currently active repository
- Data: commit histories of 76 public repositories; 3,533 samples; 2.5% positive; split **by repository**
- Leakage control: features ≤ T, labels > T, fully observed horizon, GroupKFold for model selection only

| Model | Bal. acc | Precision | Recall | F1 | ROC-AUC | PR-AUC [95% CI] |
|---|---|---|---|---|---|---|
| Rule: >60 days idle | 0.740 | 0.333 | 0.500 | **0.400** | 0.908 | 0.239 [0.14–0.45] |
| Logistic regression | **0.865** | 0.160 | **0.812** | 0.268 | **0.950** | 0.379 [0.19–0.64] |

**Finding: the model ranks better, but the intervals overlap — we do not claim it beats the simple rule.** It stays experimental and outside the risk score.

---
## Slide 12 — What-If simulator
- Move sliders (PR turnaround, backlog age, contributor share, …) → same risk engine recomputes
- Shows current vs simulated score, the difference, and per-dimension bars
- Every output labelled **SIMULATION / ESTIMATE**
*Say why: changing one metric in reality changes others; this shows model sensitivity, not the future.*

---
## Slide 13 — Results, quality, security, ethics, SDG
**Delivered:** working full-stack application — 19 endpoints, 13 tables, 22 metrics, 13 signals, dashboard with 7 views, PDF report
**Verified:** 111 backend tests on PostgreSQL 16 (97% coverage), 13 frontend tests, lint/type checks clean, `pip-audit` and `npm audit` clean, all 12 diagrams render, live GitHub rate-limit path verified against the real API
**Security:** token server-side only (tested against every response), input validation, ORM-bound queries, security headers, no stack traces, non-root container, audit log; no authentication by documented decision
**Ethics/SDG:** assesses projects, not people; minimal personal data; SDG 9 (resilient digital infrastructure), SDG 4 (quality education)
*Do not claim accuracy of the risk score — it is a heuristic.*

---
## Slide 14 — Limitations and future scope
**Limitations:** thresholds not validated · GitHub is a partial view · commit counts are a proxy · page caps truncate huge repositories · ML uses a convenience sample with only 16 positive test cases · no authentication
**Future:** validate thresholds against maintainer judgements · larger random ML sample and calibration · file-authorship truck factor · scheduled analyses · OAuth for private repositories
**Closing line:** *"A working, explainable, tested system — and honest about what it has not proven."*
