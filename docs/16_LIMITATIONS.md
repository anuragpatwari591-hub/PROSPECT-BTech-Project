# 16 — Limitations

## Validity of the risk score
- Weights and thresholds are heuristic defaults, **not calibrated or validated** against project outcomes.
- The score measures signals in GitHub activity, not "risk" in the project-management sense (budget, schedule, requirements).
- Cross-project comparison is weak: project size, age, domain and workflow change what "normal" looks like.

## Data
- Only public GitHub data; private discussions, other issue trackers (Jira), mailing lists and chat are invisible.
- Commits: default branch only; squash merges hide individual commits; commit counts are a contribution proxy.
- Merged-PR metrics miss PRs integrated by rebase/cherry-pick (GitHub shows them as closed, not merged).
- Page caps (default 5 × 100 items per endpoint) truncate very active repositories; flagged but still biased.
- PR size uses a sample of the 15 most recent merged PRs.
- Unlinked authors with several e-mail addresses count as several people.
- Bot detection relies on `[bot]` logins / GitHub type; other automation accounts may be counted as humans.

## Machine learning
- Convenience sample of 76 famous repositories; selection bias; 16 positive test samples → wide confidence intervals.
- No evidence the model beats a one-line recency rule.
- Training uses all branches from Git; serving uses default-branch API commits.
- Anomaly detection has no ground truth and is informational only.

## Engineering
- No authentication (by design for v1.0).
- Background tasks run in the API process; a restart loses in-progress runs (marked FAILED later).
- Docker images were not built in the development environment (Docker unavailable); CI builds them.
- A full live analysis of a real repository was not completed in the build environment: the shared IP's
  unauthenticated GitHub quota (60 requests/hour) was permanently exhausted by other users. Only the live
  rate-limit handling path was verified against real GitHub; run `scripts/live_smoke.py` with a token to verify
  the full path (docs/11_TESTING.md).
- History trends need repeated analyses over weeks; the system does not back-fill history.
