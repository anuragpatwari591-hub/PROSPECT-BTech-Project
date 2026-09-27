"""Default, configurable risk model.

IMPORTANT: these weights and thresholds are HEURISTIC DEFAULTS chosen by the team and informed by the
literature cited in docs/06_RISK_MODEL.md. They are NOT empirically validated. Override them with a JSON file
(RISK_CONFIG_PATH) that has the same structure.

Each signal maps one metric to a 0–100 risk score through piecewise-linear interpolation between `points`
[(metric_value, risk_score), ...]. Values outside the range are clamped to the nearest end point.
"""

DEFAULT_RISK_CONFIG: dict = {
    "version": "1.0.0",
    "levels": {"LOW": 0, "MEDIUM": 25, "HIGH": 50, "CRITICAL": 75},
    "dimensions": {
        "activity": {
            "label": "Activity risk", "weight": 0.25,
            "signals": {
                "recency": {"metric": "days_since_last_commit", "points": [[7, 0], [30, 40], [90, 100]],
                            "missing_score": 100, "label": "Time since last commit"},
                "trend": {"metric": "activity_trend_pct", "points": [[0, 0], [-40, 50], [-80, 100]],
                          "label": "Recent activity change"},
                "regularity": {"metric": "active_weeks_ratio", "points": [[0.8, 0], [0.5, 40], [0.15, 100]],
                               "label": "Weeks with commits"},
            },
        },
        "issues": {
            "label": "Issue risk", "weight": 0.2,
            "signals": {
                "close_ratio": {"metric": "issue_close_ratio_90d", "points": [[1.0, 0], [0.7, 40], [0.3, 100]],
                                "label": "Issues closed vs opened"},
                "backlog_age": {"metric": "median_open_issue_age_days", "points": [[30, 0], [120, 50], [365, 100]],
                                "label": "Median open issue age"},
            },
        },
        "pull_requests": {
            "label": "Pull request risk", "weight": 0.2,
            "signals": {
                "turnaround": {"metric": "median_pr_turnaround_days", "points": [[1, 0], [4, 50], [14, 100]],
                               "label": "Median PR turnaround"},
                "turnaround_trend": {"metric": "pr_turnaround_trend_pct", "points": [[0, 0], [50, 50], [150, 100]],
                                     "label": "PR turnaround trend"},
                "stale_prs": {"metric": "stale_open_pr_ratio", "points": [[0.1, 0], [0.4, 50], [0.7, 100]],
                              "label": "Stale open PRs"},
                "pr_size": {"metric": "median_pr_size_lines", "points": [[200, 0], [500, 50], [1500, 100]],
                            "label": "Median PR size"},
            },
        },
        "contributors": {
            "label": "Contributor dependency risk", "weight": 0.2,
            "signals": {
                "concentration": {"metric": "top_contributor_share", "points": [[0.3, 0], [0.6, 50], [0.9, 100]],
                                  "label": "Top contributor share"},
                "bus_factor": {"metric": "bus_factor_estimate", "points": [[1, 100], [2, 60], [3, 30], [4, 0]],
                               "label": "Commit-share bus factor"},
                "team_size": {"metric": "contributors_90d", "points": [[1, 100], [3, 50], [6, 0]],
                              "label": "Active contributors"},
            },
        },
        "releases": {
            "label": "Release risk", "weight": 0.15,
            "signals": {
                "release_recency": {"metric": "days_since_last_release", "points": [[90, 0], [180, 40], [540, 100]],
                                    "label": "Time since last release"},
            },
        },
    },
}
