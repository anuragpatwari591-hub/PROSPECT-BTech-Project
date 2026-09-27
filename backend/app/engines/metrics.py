"""Metric Engine — turns normalised repository data into documented software-engineering metrics.

Every metric is defined once in METRIC_DEFINITIONS (name, definition, formula, source, unit, interpretation,
limitations). docs/05_METRICS.md is generated from this dictionary, so documentation and code cannot drift.
All functions are pure: same input -> same output, no database or network access.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

RECENT_DAYS = 30
WINDOW_DAYS = 90


@dataclass
class RepoData:
    as_of: datetime
    commits: list[dict] = field(default_factory=list)      # authored_at, author_key, is_bot
    issues: list[dict] = field(default_factory=list)       # state, created_at, closed_at
    # pulls: state, created_at, updated_at, merged_at, additions, deletions
    pulls: list[dict] = field(default_factory=list)
    releases: list[dict] = field(default_factory=list)     # published_at, prerelease
    contributors: list[dict] = field(default_factory=list) # login, contributions, is_bot


@dataclass
class MetricValue:
    value: float | None
    note: str | None = None


def _d(key, name, definition, formula, source, unit, interpretation, limitations):
    return key, dict(name=name, definition=definition, formula=formula, source=source, unit=unit,
                     interpretation=interpretation, limitations=limitations)


METRIC_DEFINITIONS: dict[str, dict] = dict([
    _d("commits_90d", "Commits (90 days)", "Number of non-bot commits authored in the last 90 days.",
       "count(commits where as_of − 90d < authored_at ≤ as_of and not bot)", "GET /repos/{o}/{r}/commits",
       "commits", "Overall development volume. Compare against the project's own history, not other projects.",
       "Counts only the default branch. Squash-merges collapse many changes into one commit. Page caps can "
       "truncate busy repositories (flagged in the run)."),
    _d("commit_frequency_per_week", "Commit frequency", "Average non-bot commits per week over 90 days.",
       "commits_90d / (90 / 7)", "Commits endpoint", "commits/week",
       "Pace of change on the default branch.", "Same as commits_90d; commit granularity differs by team habit."),
    _d("active_weeks_ratio", "Active weeks ratio", "Share of the last 13 weeks that had at least one non-bot commit.",
       "weeks_with_commits(13) / 13", "Commits endpoint", "ratio 0–1",
       "Regularity of activity; low values indicate bursty or stalled work.",
       "A project that commits once a week and one that commits 100 times a week score the same."),
    _d("activity_trend_pct", "Activity trend", "Change in commit rate in the last 30 days relative to the "
       "preceding 60 days.", "(c30 − c60/2) / (c60/2) × 100, capped to [−100, +100]; null if both are 0",
       "Commits endpoint", "%", "Negative = recent slowdown; positive = acceleration.",
       "Sensitive to holidays and release cycles; one month is a short baseline."),
    _d("days_since_last_commit", "Days since last commit", "Days between the analysis time and the most recent "
       "non-bot commit in the collected window.", "as_of − max(authored_at)", "Commits endpoint", "days",
       "Recency of development.", "Null if no commits in the collection window (reported as window length)."),
    _d("open_issues", "Open issues", "Number of currently open issues (pull requests excluded).",
       "count(issues where state = open)", "GET /repos/{o}/{r}/issues?state=open", "issues",
       "Size of the backlog. Popular projects naturally have more issues.",
       "Not normalised by project size; truncated when above the page cap."),
    _d("issues_opened_90d", "Issues opened (90 days)", "Issues created in the last 90 days.",
       "count(created_at in window)", "Issues endpoint", "issues", "Incoming demand / defect reports.",
       "Depends on the project's use of GitHub Issues."),
    _d("issues_closed_90d", "Issues closed (90 days)", "Issues closed in the last 90 days.",
       "count(closed_at in window)", "Issues endpoint", "issues", "Maintainer throughput on the backlog.",
       "Closing as 'won't fix' counts the same as fixing."),
    _d("issue_close_ratio_90d", "Issue close ratio", "Issues closed divided by issues opened in the last 90 days.",
       "issues_closed_90d / issues_opened_90d; null if none opened", "Issues endpoint", "ratio",
       "≥ 1 means the backlog is shrinking; < 1 means it is growing.",
       "Closed issues may have been opened before the window."),
    _d("median_open_issue_age_days", "Median open issue age", "Median age of currently open issues.",
       "median(as_of − created_at) over open issues", "Issues endpoint", "days",
       "Higher values suggest issues are not being triaged.",
       "Long-lived feature requests inflate this legitimately."),
    _d("median_issue_resolution_days", "Median issue resolution time", "Median time from creation to "
       "closure for issues closed in the last 90 days.", "median(closed_at − created_at)", "Issues endpoint",
       "days", "Responsiveness to reported issues.", "Survivor bias: only closed issues are measured."),
    _d("open_prs", "Open pull requests", "Number of currently open pull requests.", "count(state = open)",
       "GET /repos/{o}/{r}/pulls?state=open", "PRs", "Review queue size.", "Includes drafts."),
    _d("prs_merged_90d", "PRs merged (90 days)", "Pull requests merged in the last 90 days.",
       "count(merged_at in window)", "Pulls endpoint", "PRs", "Integration throughput.",
       "Projects that push directly to main will show low values."),
    _d("median_pr_turnaround_days", "Median PR turnaround", "Median time from PR creation to merge for PRs "
       "merged in the last 90 days.", "median(merged_at − created_at)", "Pulls endpoint", "days",
       "Longer turnaround is associated with review bottlenecks (Gousios et al., 2014 study merge time factors).",
       "Excludes PRs closed without merge; drafts opened early inflate it."),
    _d("pr_turnaround_trend_pct", "PR turnaround trend", "Change in median turnaround for PRs merged in the "
       "last 30 days versus the preceding 60 days.", "(m30 − m60) / m60 × 100, capped to [−100, +300]",
       "Pulls endpoint", "%", "Positive = reviews are getting slower.",
       "Needs at least 3 merged PRs in each period, otherwise null."),
    _d("stale_open_pr_ratio", "Stale open PR ratio", "Share of open PRs not updated for more than 30 days.",
       "count(open and as_of − updated_at > 30d) / open_prs", "Pulls endpoint", "ratio 0–1",
       "Abandoned or blocked review work.", "Null when there are no open PRs."),
    _d("median_pr_size_lines", "Median PR size", "Median of additions + deletions over a sample of recently "
       "merged PRs.", "median(additions + deletions)", "GET /repos/{o}/{r}/pulls/{n} (sampled)", "lines",
       "Large PRs are harder to review.", "Sample of the most recent merged PRs only (PR_DETAIL_SAMPLE); "
       "generated files and lockfiles inflate size."),
    _d("contributors_90d", "Active contributors (90 days)", "Distinct non-bot commit authors in the last 90 days.",
       "count(distinct author_key)", "Commits endpoint", "people",
       "Breadth of the active team.", "One person with two e-mails may count twice when accounts are unlinked."),
    _d("top_contributor_share", "Top contributor share", "Share of the last 90 days' non-bot commits made "
       "by the single most active author.", "max(commits_by_author) / commits_90d", "Commits endpoint",
       "ratio 0–1", "High values mean knowledge and progress depend on one person.",
       "Commit counts are a proxy for contribution; reviews, design and triage are invisible."),
    _d("bus_factor_estimate", "Commit-share bus factor (estimate)", "Smallest number of authors who together "
       "made at least 50% of non-bot commits in the last 90 days.",
       "min k such that sum of top-k author commit counts ≥ 0.5 × commits_90d", "Commits endpoint", "people",
       "1 = a single person carries half the work. A simplified heuristic, NOT the file-ownership truck-factor "
       "algorithm of Avelino et al. (2016).", "Ignores code ownership and expertise; short window."),
    _d("releases_365d", "Releases (365 days)", "Published, non-draft releases in the last year.",
       "count(published_at within 365 days)", "GET /repos/{o}/{r}/releases (first 100)", "releases",
       "Delivery cadence for projects that use GitHub Releases.",
       "Many projects tag versions without GitHub Releases; then release metrics are not applicable."),
    _d("days_since_last_release", "Days since last release", "Days since the most recent published release.",
       "as_of − max(published_at)", "Releases endpoint", "days", "Delivery recency.",
       "Null when the project has never published a GitHub Release."),
])


def _median(values) -> float | None:
    arr = [v for v in values if v is not None]
    return float(np.median(arr)) if arr else None


def _days(delta: timedelta) -> float:
    return delta.total_seconds() / 86400


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(float(value), digits)


def compute_metrics(data: RepoData) -> dict[str, MetricValue]:
    now = data.as_of
    w_start, r_start = now - timedelta(days=WINDOW_DAYS), now - timedelta(days=RECENT_DAYS)
    out: dict[str, MetricValue] = {}

    human_commits = [c for c in data.commits if not c["is_bot"] and c["authored_at"] <= now]
    window = [c for c in human_commits if c["authored_at"] > w_start]
    c30 = sum(1 for c in window if c["authored_at"] > r_start)
    c60 = len(window) - c30
    out["commits_90d"] = MetricValue(len(window))
    out["commit_frequency_per_week"] = MetricValue(_round(len(window) / (WINDOW_DAYS / 7)))
    active_weeks = {int(_days(now - c["authored_at"]) // 7) for c in window}
    out["active_weeks_ratio"] = MetricValue(_round(len({w for w in active_weeks if w < 13}) / 13))
    baseline = c60 / 2
    if c30 == 0 and baseline == 0:
        out["activity_trend_pct"] = MetricValue(None, "No commits in the last 90 days.")
    elif baseline == 0:
        out["activity_trend_pct"] = MetricValue(100.0, "No commits in the baseline period; capped at +100%.")
    else:
        trend = (c30 - baseline) / baseline * 100
        out["activity_trend_pct"] = MetricValue(_round(max(-100.0, min(100.0, trend)), 1))
    if human_commits:
        latest = max(c["authored_at"] for c in human_commits)
        out["days_since_last_commit"] = MetricValue(_round(_days(now - latest), 1))
    else:
        out["days_since_last_commit"] = MetricValue(None, "No non-bot commits in the collection window.")

    open_issues = [i for i in data.issues if i["state"] == "open"]
    opened = sum(1 for i in data.issues if i["created_at"] > w_start)
    closed = [i for i in data.issues if i["closed_at"] and i["closed_at"] > w_start]
    out["open_issues"] = MetricValue(len(open_issues))
    out["issues_opened_90d"] = MetricValue(opened)
    out["issues_closed_90d"] = MetricValue(len(closed))
    out["issue_close_ratio_90d"] = MetricValue(_round(len(closed) / opened) if opened else None,
                                               None if opened else "No issues opened in the last 90 days.")
    open_ages = (_days(now - i["created_at"]) for i in open_issues)
    out["median_open_issue_age_days"] = MetricValue(_round(_median(open_ages), 1))
    out["median_issue_resolution_days"] = MetricValue(
        _round(_median(_days(i["closed_at"] - i["created_at"]) for i in closed), 1))

    open_prs = [p for p in data.pulls if p["state"] == "open"]
    merged = [p for p in data.pulls if p["merged_at"] and p["merged_at"] > w_start]
    out["open_prs"] = MetricValue(len(open_prs))
    out["prs_merged_90d"] = MetricValue(len(merged))
    out["median_pr_turnaround_days"] = MetricValue(
        _round(_median(_days(p["merged_at"] - p["created_at"]) for p in merged), 2),
        None if merged else "No pull requests merged in the last 90 days.")
    recent = [_days(p["merged_at"] - p["created_at"]) for p in merged if p["merged_at"] > r_start]
    older = [_days(p["merged_at"] - p["created_at"]) for p in merged if p["merged_at"] <= r_start]
    if len(recent) >= 3 and len(older) >= 3 and _median(older) > 0:
        trend = (_median(recent) - _median(older)) / _median(older) * 100
        out["pr_turnaround_trend_pct"] = MetricValue(_round(max(-100.0, min(300.0, trend)), 1))
    else:
        out["pr_turnaround_trend_pct"] = MetricValue(None, "Fewer than 3 merged PRs in one of the periods.")
    if open_prs:
        stale = sum(1 for p in open_prs if _days(now - (p["updated_at"] or p["created_at"])) > 30)
        out["stale_open_pr_ratio"] = MetricValue(_round(stale / len(open_prs)))
    else:
        out["stale_open_pr_ratio"] = MetricValue(None, "No open pull requests.")
    sizes = [(p["additions"] or 0) + (p["deletions"] or 0) for p in data.pulls
             if p["merged_at"] and p.get("additions") is not None]
    out["median_pr_size_lines"] = MetricValue(_round(_median(sizes), 0),
                                              f"Sample of {len(sizes)} merged PRs." if sizes else "No PR size sample.")

    counts = pd.Series([c["author_key"] for c in window]).value_counts() if window else pd.Series(dtype=int)
    out["contributors_90d"] = MetricValue(int(counts.size))
    if counts.size:
        out["top_contributor_share"] = MetricValue(_round(counts.iloc[0] / counts.sum()))
        cumulative = counts.cumsum() / counts.sum()
        out["bus_factor_estimate"] = MetricValue(int((cumulative < 0.5).sum() + 1))
    else:
        out["top_contributor_share"] = MetricValue(None, "No commits in the last 90 days.")
        out["bus_factor_estimate"] = MetricValue(None, "No commits in the last 90 days.")

    published = [r["published_at"] for r in data.releases if r["published_at"]]
    out["releases_365d"] = MetricValue(sum(1 for t in published if t > now - timedelta(days=365)))
    out["days_since_last_release"] = MetricValue(
        _round(_days(now - max(published)), 1) if published else None,
        None if published else "The project has no GitHub Releases.")
    return out


def weekly_activity(data: RepoData, weeks: int = 52) -> pd.DataFrame:
    """Weekly counts for charts and anomaly detection. Weeks are counted backwards from as_of (week 0 = current)."""
    start = data.as_of - timedelta(weeks=weeks)
    index = pd.date_range(end=data.as_of, periods=weeks, freq="7D")
    frame = pd.DataFrame(0, index=range(weeks), columns=["commits", "issues_opened", "issues_closed",
                                                         "prs_opened", "prs_merged"])

    def bucket(ts: datetime | None) -> int | None:
        if ts is None or ts <= start or ts > data.as_of:
            return None
        return weeks - 1 - int(_days(data.as_of - ts) // 7)

    for c in data.commits:
        if not c["is_bot"] and (b := bucket(c["authored_at"])) is not None:
            frame.loc[b, "commits"] += 1
    for i in data.issues:
        if (b := bucket(i["created_at"])) is not None:
            frame.loc[b, "issues_opened"] += 1
        if (b := bucket(i["closed_at"])) is not None:
            frame.loc[b, "issues_closed"] += 1
    for p in data.pulls:
        if (b := bucket(p["created_at"])) is not None:
            frame.loc[b, "prs_opened"] += 1
        if (b := bucket(p["merged_at"])) is not None:
            frame.loc[b, "prs_merged"] += 1
    frame.insert(0, "week_ending", [d.date().isoformat() for d in index])
    return frame
