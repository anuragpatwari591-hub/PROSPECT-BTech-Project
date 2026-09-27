# PROSPECT Risk Algorithm

PROSPECT scores every repository with the exact same deterministic,
rule-based algorithm (`backend/app/risk_engine.py`). There is no machine
learning model, no training data, and no per-repository special-casing.
Given the same input metrics, the algorithm always produces the same
output — this is what makes the score explainable and reproducible.

## Overview

1. The GitHub client (`backend/app/github_client.py`) collects **real** data
   from the GitHub REST API: repository metadata, up to 300 recent commits,
   up to 200 contributors, up to 300 issues, up to 300 pull requests, and up
   to 200 releases.
2. That raw data is normalized into a `RepoMetrics` object — plain counts and
   ratios, nothing fabricated.
3. Five independent scoring functions each look at one dimension of risk and
   return a number of points (out of a fixed maximum) plus a plain-English
   explanation of *why*.
4. The five category scores are summed into a single **Risk Score (0-100)**.
5. **Health Score = 100 − Risk Score.**
6. The Risk Score is mapped to a classification band.

## Categories and maximum points (sum to 100)

| Category | Max Points | What it measures |
|---|---|---|
| Repository Activity | 25 | How recently the repository was pushed to |
| Issue Management | 20 | Open/closed ratio and how many issues are stale (>90 days) |
| Pull Request Health | 15 | Merge rate and how many open PRs are stale (>45 days) |
| Contributor Dependency (Bus Factor) | 25 | Number of contributors and how concentrated commits are in one person |
| Release Cadence | 15 | Whether releases exist and how recently the last one shipped |

### 1. Repository Activity (max 25)

* Archived repository → **25** (maximum risk, repository is explicitly dead).
* No commit history found → **25**.
* Otherwise, based on days since the last push:

  | Days since last push | Points |
  |---|---|
  | ≤ 7 | 0 |
  | ≤ 30 | 5 |
  | ≤ 90 | 10 |
  | ≤ 180 | 15 |
  | ≤ 365 | 20 |
  | > 365 | 25 |

### 2. Issue Management (max 20)

* `open_ratio = open_issues / (open_issues + closed_issues)` → up to **10**
  points, scaled linearly (`round(open_ratio * 10)`).
* `stale_ratio = stale_open_issues / open_issues` (stale = open > 90 days) →
  up to **10** points, scaled linearly.
* No issues at all → **0** (absence of data is never treated as risk).

### 3. Pull Request Health (max 15)

* `unmerged_ratio = closed_unmerged / (closed_unmerged + merged)` → up to
  **8** points.
* If PRs are open but none has ever been closed/merged, that also scores
  **8** (no track record of review throughput).
* `stale_ratio = stale_open_prs / open_prs` (stale = open > 45 days) → up to
  **7** points.

### 4. Contributor Dependency / Bus Factor (max 25)

Two independent signals are added together (capped at 25):

* Contributor count:

  | Contributors | Points |
  |---|---|
  | ≤ 1 | 15 |
  | 2 | 10 |
  | 3–4 | 5 |
  | 5–9 | 2 |
  | ≥ 10 | 0 |

* Share of sampled commits by the single top contributor:

  | Top contributor share | Points |
  |---|---|
  | ≥ 90% | 10 |
  | ≥ 75% | 7 |
  | ≥ 50% | 4 |
  | ≥ 30% | 2 |
  | < 30% | 0 |

### 5. Release Cadence (max 15)

* No releases ever published → **10** (moderate, not maximum — many healthy
  projects don't use GitHub Releases).
* Otherwise, based on days since the last release:

  | Days since last release | Points |
  |---|---|
  | ≤ 90 | 0 |
  | ≤ 180 | 4 |
  | ≤ 365 | 8 |
  | ≤ 730 | 12 |
  | > 730 | 15 |

## Classification

| Risk Score | Classification |
|---|---|
| 0–25 | LOW |
| 26–50 | MEDIUM |
| 51–75 | HIGH |
| 76–100 | CRITICAL |

## Recommendations

For every category where the awarded points are ≥ 50% of that category's
maximum, a fixed, category-specific recommendation is included in the
result. If no category crosses that threshold, PROSPECT reports that no
significant risk factors were found.

## What-If Simulator

The What-If simulator (`POST /api/whatif/{id}`) takes the metrics stored
from a real analysis, applies user-supplied overrides to any subset of
`RepoMetrics` fields, and re-runs **the same** `calculate_risk()` function.
No new GitHub API calls are made — it is a pure re-computation, which is why
it is instant and always consistent with the real analysis it started from.

## Why this design

* **Transparent** — every point traces back to one `if` branch a reader can
  point to.
* **Deterministic** — same metrics in, same score out, always.
* **Explainable** — every factor carries plain-English reasons, not just a
  number.
* **No special-casing** — the engine never sees a repository's name or URL,
  only its metrics, so it is structurally impossible to hard-code a
  favorable score for any specific project (including PROSPECT's own
  repository).
