"""
Deterministic, rule-based risk engine.

Every score is produced by fixed, documented thresholds applied to metrics
collected from the GitHub REST API (see github_client.py). There is no
machine learning, no randomness and no repository-specific special-casing:
the exact same function, given the exact same metrics, always produces the
exact same score. See docs/RISK_ALGORITHM.md for the full write-up.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional


# ---------------------------------------------------------------------------
# Input: the normalized metrics the engine scores. Anything upstream (the
# GitHub client, or the What-If simulator) just needs to produce one of these.
# ---------------------------------------------------------------------------
@dataclass
class RepoMetrics:
    archived: bool = False

    days_since_last_push: Optional[int] = None  # None => unknown/no commits

    contributor_count: int = 0
    top_contributor_pct: float = 0.0  # 0-100, share of sampled commits by the top author

    open_issue_count: int = 0
    closed_issue_count: int = 0
    stale_open_issue_count: int = 0  # open issues older than STALE_ISSUE_DAYS

    open_pr_count: int = 0
    closed_unmerged_pr_count: int = 0
    merged_pr_count: int = 0
    stale_open_pr_count: int = 0  # open PRs older than STALE_PR_DAYS

    release_count: int = 0
    days_since_last_release: Optional[int] = None  # None => no releases ever

    def to_dict(self):
        return asdict(self)


@dataclass
class RiskFactor:
    key: str
    label: str
    points: float
    max_points: float
    reasons: List[str] = field(default_factory=list)

    @property
    def pct_of_max(self) -> float:
        if self.max_points == 0:
            return 0.0
        return round((self.points / self.max_points) * 100, 1)

    def to_dict(self):
        d = asdict(self)
        d["pct_of_max"] = self.pct_of_max
        return d


@dataclass
class RiskResult:
    risk_score: float
    health_score: float
    classification: str
    factors: List[RiskFactor]
    recommendations: List[str]

    def to_dict(self):
        return {
            "risk_score": self.risk_score,
            "health_score": self.health_score,
            "classification": self.classification,
            "factors": [f.to_dict() for f in self.factors],
            "recommendations": self.recommendations,
        }


# ---------------------------------------------------------------------------
# Category scorers. Each returns a RiskFactor with points capped at its
# documented maximum. Max points across all five categories sum to 100.
# ---------------------------------------------------------------------------

def score_activity(metrics: RepoMetrics) -> RiskFactor:
    max_points = 25.0
    reasons = []

    if metrics.archived:
        return RiskFactor(
            key="activity",
            label="Repository Activity",
            points=max_points,
            max_points=max_points,
            reasons=["Repository is archived and is no longer maintained."],
        )

    days = metrics.days_since_last_push
    if days is None:
        points = max_points
        reasons.append("No commit history was found for this repository.")
    elif days <= 7:
        points = 0.0
        reasons.append(f"Last push was {days} day(s) ago — actively maintained.")
    elif days <= 30:
        points = 5.0
        reasons.append(f"Last push was {days} days ago — recently active.")
    elif days <= 90:
        points = 10.0
        reasons.append(f"Last push was {days} days ago — activity has slowed.")
    elif days <= 180:
        points = 15.0
        reasons.append(f"Last push was {days} days ago — activity is low.")
    elif days <= 365:
        points = 20.0
        reasons.append(f"Last push was {days} days ago — repository looks inactive.")
    else:
        points = 25.0
        reasons.append(f"Last push was {days} days ago — repository appears abandoned.")

    return RiskFactor("activity", "Repository Activity", points, max_points, reasons)


def score_issues(metrics: RepoMetrics) -> RiskFactor:
    max_points = 20.0
    reasons = []

    total = metrics.open_issue_count + metrics.closed_issue_count
    if total == 0:
        reasons.append("No issues found in the sampled history.")
        return RiskFactor("issues", "Issue Management", 0.0, max_points, reasons)

    open_ratio = metrics.open_issue_count / total
    open_points = round(open_ratio * 10, 1)
    reasons.append(
        f"{metrics.open_issue_count} of {total} sampled issues are open "
        f"({open_ratio * 100:.0f}% open ratio)."
    )

    if metrics.open_issue_count > 0:
        stale_ratio = metrics.stale_open_issue_count / metrics.open_issue_count
    else:
        stale_ratio = 0.0
    stale_points = round(stale_ratio * 10, 1)
    if metrics.stale_open_issue_count > 0:
        reasons.append(
            f"{metrics.stale_open_issue_count} open issue(s) have been unresolved "
            f"for over 90 days."
        )

    points = min(open_points + stale_points, max_points)
    return RiskFactor("issues", "Issue Management", points, max_points, reasons)


def score_pull_requests(metrics: RepoMetrics) -> RiskFactor:
    max_points = 15.0
    reasons = []

    closed_total = metrics.closed_unmerged_pr_count + metrics.merged_pr_count
    if closed_total == 0:
        merge_points = 8.0 if metrics.open_pr_count > 0 else 0.0
        if metrics.open_pr_count > 0:
            reasons.append(
                "No pull requests have ever been merged or closed, so review "
                "throughput cannot be established."
            )
    else:
        unmerged_ratio = metrics.closed_unmerged_pr_count / closed_total
        merge_points = round(unmerged_ratio * 8, 1)
        reasons.append(
            f"{metrics.merged_pr_count} of {closed_total} closed pull requests were "
            f"merged ({(1 - unmerged_ratio) * 100:.0f}% merge rate)."
        )

    if metrics.open_pr_count > 0:
        stale_ratio = metrics.stale_open_pr_count / metrics.open_pr_count
    else:
        stale_ratio = 0.0
    stale_points = round(stale_ratio * 7, 1)
    if metrics.stale_open_pr_count > 0:
        reasons.append(
            f"{metrics.stale_open_pr_count} open pull request(s) have been waiting "
            f"for over 45 days."
        )

    points = min(merge_points + stale_points, max_points)
    return RiskFactor("pull_requests", "Pull Request Health", points, max_points, reasons)


def score_contributors(metrics: RepoMetrics) -> RiskFactor:
    max_points = 25.0
    reasons = []

    count = metrics.contributor_count
    if count <= 1:
        count_points = 15.0
        reasons.append("Only a single contributor was found — high bus-factor risk.")
    elif count == 2:
        count_points = 10.0
        reasons.append("Only 2 contributors were found — limited redundancy.")
    elif count <= 4:
        count_points = 5.0
        reasons.append(f"{count} contributors found — a small core team.")
    elif count <= 9:
        count_points = 2.0
        reasons.append(f"{count} contributors found — a moderately sized team.")
    else:
        count_points = 0.0
        reasons.append(f"{count} contributors found — a broad contributor base.")

    pct = metrics.top_contributor_pct
    if pct >= 90:
        pct_points = 10.0
        reasons.append(f"The top contributor authored {pct:.0f}% of sampled commits.")
    elif pct >= 75:
        pct_points = 7.0
        reasons.append(f"The top contributor authored {pct:.0f}% of sampled commits.")
    elif pct >= 50:
        pct_points = 4.0
        reasons.append(f"The top contributor authored {pct:.0f}% of sampled commits.")
    elif pct >= 30:
        pct_points = 2.0
    else:
        pct_points = 0.0

    points = min(count_points + pct_points, max_points)
    return RiskFactor("contributors", "Contributor Dependency (Bus Factor)", points, max_points, reasons)


def score_releases(metrics: RepoMetrics) -> RiskFactor:
    max_points = 15.0
    reasons = []

    if metrics.release_count == 0:
        reasons.append("No versioned GitHub releases were found for this repository.")
        return RiskFactor("releases", "Release Cadence", 10.0, max_points, reasons)

    days = metrics.days_since_last_release
    if days is None:
        points = 10.0
        reasons.append("Release history is inconclusive.")
    elif days <= 90:
        points = 0.0
        reasons.append(f"Last release was {days} day(s) ago — healthy cadence.")
    elif days <= 180:
        points = 4.0
        reasons.append(f"Last release was {days} days ago.")
    elif days <= 365:
        points = 8.0
        reasons.append(f"Last release was {days} days ago — cadence has slowed.")
    elif days <= 730:
        points = 12.0
        reasons.append(f"Last release was {days} days ago — releases are infrequent.")
    else:
        points = 15.0
        reasons.append(f"Last release was {days} days ago — releases appear to have stopped.")

    return RiskFactor("releases", "Release Cadence", points, max_points, reasons)


CLASSIFICATION_THRESHOLDS = (
    (25, "LOW"),
    (50, "MEDIUM"),
    (75, "HIGH"),
    (100, "CRITICAL"),
)


def classify(risk_score: float) -> str:
    for threshold, label in CLASSIFICATION_THRESHOLDS:
        if risk_score <= threshold:
            return label
    return "CRITICAL"


RECOMMENDATIONS = {
    "activity": "Increase development activity: schedule regular commits or "
    "confirm whether this project is still actively maintained.",
    "issues": "Triage the open issue backlog and close or respond to issues "
    "older than 90 days to keep the tracker actionable.",
    "pull_requests": "Improve pull request throughput: review and merge or "
    "close pending pull requests promptly, especially ones waiting over 45 days.",
    "contributors": "Reduce bus-factor risk by onboarding additional "
    "contributors and avoiding concentration of knowledge in a single author.",
    "releases": "Adopt a regular release cadence using GitHub Releases so "
    "consumers can track stable, versioned milestones.",
}


def calculate_risk(metrics: RepoMetrics) -> RiskResult:
    factors = [
        score_activity(metrics),
        score_issues(metrics),
        score_pull_requests(metrics),
        score_contributors(metrics),
        score_releases(metrics),
    ]

    risk_score = round(min(sum(f.points for f in factors), 100.0), 1)
    health_score = round(100.0 - risk_score, 1)
    classification = classify(risk_score)

    recommendations = [
        RECOMMENDATIONS[f.key] for f in factors if f.pct_of_max >= 50.0
    ]
    if not recommendations:
        recommendations.append(
            "No significant risk factors detected. Keep up the current "
            "maintenance practices."
        )

    return RiskResult(risk_score, health_score, classification, factors, recommendations)
