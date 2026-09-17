# 17 — Future Scope

1. **Validate the risk model:** collect maintainer judgements or outcomes (deprecation, archival, security incidents) and calibrate thresholds; report agreement statistics.
2. **Better ML evaluation:** larger random sample (e.g. via GH Archive/World of Code), temporal hold-out by calendar year, calibration curves, threshold selection for a target precision.
3. **Truck factor:** implement a file-authorship algorithm (Avelino et al., 2016) and compare with the commit-share estimate.
4. **Authentication and multi-tenancy:** accounts, per-user projects, GitHub OAuth for private repositories.
5. **Scheduled re-analysis:** a job queue (e.g. Celery/RQ or a platform cron) to build history automatically.
6. **Incremental collection:** conditional requests with ETags and `since` cursors to cut API usage.
7. **More sources:** GitLab, Jira, CI results (GitHub Actions failure rate), dependency vulnerability data.
8. **Team-specific baselines:** score deviations from a project's own history instead of fixed thresholds.
9. **Notifications:** alerts when risk level rises between runs.
10. **Accessibility audit and user study** of whether explanations help users make decisions.
