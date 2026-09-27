# PROSPECT — Viva Cheat Sheet (one page)

**One sentence:** PROSPECT collects GitHub development activity, turns it into 22 documented metrics, and produces an explainable 0–100 risk score with factor-level contributions, linked recommendations, What-If simulation, history and PDF reports.

## Numbers to remember
| Item | Value |
|---|---|
| Metrics / signals / dimensions | 22 / 13 / 5 |
| Dimension weights | Activity 0.25 · Issues 0.20 · PRs 0.20 · Contributors 0.20 · Releases 0.15 |
| Level cut-offs | LOW < 25 ≤ MEDIUM < 50 ≤ HIGH < 75 ≤ CRITICAL |
| Recommendation trigger | signal ≥ 50 (HIGH priority ≥ 75) |
| Tables | 13 |
| Backend tests / coverage | 111 on PostgreSQL 16 / 97% |
| Frontend tests | 13 |
| GitHub limits | 60 req/h without token, 5,000 with |
| Collection defaults | 365-day window, 5 pages × 100 per endpoint, 15 PR size samples, 30-min cache |
| ML dataset | 76 repos · 3,533 samples · 2.5% positive · 60 train / 16 test repos |
| LR test | ROC-AUC 0.950 [0.907–0.981] · PR-AUC 0.379 [0.189–0.639] · P 0.16 · R 0.81 · F1 0.27 |
| Rule (>60 days) test | ROC-AUC 0.908 · PR-AUC 0.239 [0.142–0.445] · F1 0.40 |
| Majority baseline accuracy | 98.1% (why accuracy is useless here) |

## Formulas
- Signal score: piecewise-linear between threshold points, clamped 0–100.
- Dimension score = mean(signal scores with data).
- Risk = Σ w'_d × dimension_d, where w'_d = w_d / Σ(weights of dimensions with data).
- Contribution(signal) = w'_d × signal / n_signals_in_d → contributions sum to risk.
- Health = 100 − risk. Coverage = Σ applicable weights / Σ all weights.
- Activity trend = (c30 − c60/2)/(c60/2) × 100, capped ±100.
- Commit-share bus factor = min k with top-k authors ≥ 50% of 90-day commits (NOT Avelino's algorithm).
- LR explanation: contribution_j = coef_j × z_j (log-odds), exact.

## Pipeline (say it in order)
URL → validate → register (1 GitHub call) → POST analyze (202) → background task → paginate GitHub (token, retries, rate-limit) → normalise (drop PRs from issues, flag bots, hash unlinked authors) → upsert in PostgreSQL (rollback on error) → metrics → risk → recommendations → ML (separate) → UI polls → dashboard → What-If → PDF.

## Honesty lines (use them)
- "The score is a transparent heuristic; the thresholds are not validated."
- "There is no real risk label, so we did not fabricate one; we predicted an observable outcome instead."
- "Our model ranks well but the confidence intervals overlap with a one-line rule, so we don't claim it's better."
- "The simulator shows model sensitivity, not the future."
- "Commit counts measure activity, not people's value."

## Leakage controls (4)
Features ≤ T, labels > T · last cutoff ≤ collection date − 180 d · split by repository · model selection by GroupKFold on train only.

## Security (6)
Token server-side `SecretStr`, never returned (tested) · Pydantic + URL regex · ORM bound parameters · CORS allow-list + security headers · generic 500s · non-root container, private DB. No auth by documented decision.

## Key related work
Kalliamvakou et al. MSR 2014 (perils of mining GitHub) · Gousios et al. ICSE 2014 (pull-based development) · Avelino et al. ICPC 2016 (truck factor) · Coelho & Valente FSE 2017 (why projects fail) · Coelho et al. ESEM 2018 (unmaintained projects) · Tantithamthavorn et al. (XAI for SE) · Liu et al. ICDM 2008 (Isolation Forest).

## If you forget everything else
**Collect → Measure → Score → Explain → Recommend → Simulate → Track → Report — and be honest about what is validated.**
