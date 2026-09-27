"""Rule-based Recommendation Engine.

A rule fires when the linked signal's score reaches `min_score`. Priority is HIGH when the score is ≥ 75,
MEDIUM when ≥ 50. Every recommendation carries the signal key (and, once stored, the RiskFactor id) that
triggered it, so users can trace advice back to evidence. Advice is generic engineering practice, not a
guarantee of improvement.
"""

from dataclasses import dataclass

from app.engines.risk import RiskResult, SignalResult


@dataclass
class RecommendationResult:
    signal_key: str
    priority: str
    title: str
    detail: str


RULES: dict[str, dict] = {
    "activity.recency": {"title": "Confirm the project is still actively maintained",
        "detail": "No recent commits ({value} days). Check whether work moved to another branch or repository, "
                  "and publish the maintenance status in the README so users can plan."},
    "activity.trend": {"title": "Review why development activity dropped",
        "detail": "Commit rate changed by {value}% versus the previous two months. Compare against the sprint or "
                  "release plan and check for blocked work, staffing changes or unclear priorities."},
    "activity.regularity": {"title": "Make development work more regular",
        "detail": "Only {pct} of the last 13 weeks had commits. Break work into smaller increments that are "
                  "merged continuously instead of in rare bursts."},
    "issues.close_ratio": {"title": "Triage and prioritise the issue backlog",
        "detail": "Issues are closed at {value}× the rate they are opened, so the backlog is growing. Schedule a "
                  "recurring triage session, label by priority, and close duplicates or stale requests."},
    "issues.backlog_age": {"title": "Address long-standing open issues",
        "detail": "Median open issue age is {value} days. Review the oldest issues: fix, schedule, or close them "
                  "with an explanation."},
    "pull_requests.turnaround": {"title": "Reduce pull request review time",
        "detail": "PRs take a median of {value} days to merge. Define review ownership (e.g. CODEOWNERS), set a "
                  "review response target, and encourage smaller PRs."},
    "pull_requests.turnaround_trend": {"title": "Investigate slowing code reviews",
        "detail": "Median PR turnaround rose by {value}% recently. Check reviewer availability and queue size."},
    "pull_requests.stale_prs": {"title": "Clean up stale pull requests",
        "detail": "{pct} of open PRs have had no activity for 30+ days. Close abandoned PRs or assign a reviewer "
                  "to finish them."},
    "pull_requests.pr_size": {"title": "Keep pull requests small",
        "detail": "Median merged PR changes {value} lines. Split features into smaller, independently reviewable "
                  "PRs; exclude generated files from diffs."},
    "contributors.concentration": {"title": "Spread knowledge beyond the top contributor",
        "detail": "One author made {pct} of recent commits. Pair on critical areas, document architecture and "
                  "release steps, and rotate code-review responsibility."},
    "contributors.bus_factor": {"title": "Build contributor redundancy",
        "detail": "About {value} author(s) produced half of recent commits. Identify single points of knowledge "
                  "and make sure at least two people can maintain each critical component."},
    "contributors.team_size": {"title": "Grow the active contributor base",
        "detail": "Only {value} people committed in the last 90 days. Label good first issues, improve "
                  "CONTRIBUTING.md, and review external contributions promptly."},
    "releases.release_recency": {"title": "Re-establish a release cadence",
        "detail": "The last release was {value} days ago. If changes are ready, publish a release with notes; "
                  "otherwise document the release policy."},
}


def _render(template: str, signal: SignalResult) -> str:
    value = signal.metric_value
    pct = "n/a" if value is None else f"{value * 100:.0f}%"
    if value is None:
        shown = "n/a"
    elif float(value).is_integer() or abs(value) >= 10:
        shown = f"{value:.0f}"
    else:
        shown = f"{value:.1f}"
    return template.format(value=shown, pct=pct)


def generate_recommendations(result: RiskResult, min_score: float = 50.0) -> list[RecommendationResult]:
    recs = []
    for signal in sorted(result.signals, key=lambda s: s.contribution, reverse=True):
        rule = RULES.get(signal.key)
        if rule and signal.score >= min_score:
            recs.append(RecommendationResult(signal.key, "HIGH" if signal.score >= 75 else "MEDIUM",
                                             rule["title"], _render(rule["detail"], signal)))
    return recs
