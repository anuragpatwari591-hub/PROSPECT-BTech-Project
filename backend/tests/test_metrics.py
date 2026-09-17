from datetime import UTC, datetime, timedelta

import pytest

from app.engines.metrics import METRIC_DEFINITIONS, RepoData, compute_metrics, weekly_activity

NOW = datetime(2026, 9, 1, tzinfo=UTC)


def ago(days):
    return NOW - timedelta(days=days)


def commit(days, author="alice", bot=False):
    return {"authored_at": ago(days), "author_key": author, "is_bot": bot}


def test_every_metric_is_documented():
    values = compute_metrics(RepoData(as_of=NOW))
    assert set(values) == set(METRIC_DEFINITIONS)
    for definition in METRIC_DEFINITIONS.values():
        assert {"name", "definition", "formula", "source", "unit", "interpretation", "limitations"} <= set(definition)
        assert all(definition.values())


def test_empty_repository_produces_nulls_not_errors():
    m = compute_metrics(RepoData(as_of=NOW))
    assert m["commits_90d"].value == 0
    assert m["days_since_last_commit"].value is None and m["days_since_last_commit"].note
    assert m["activity_trend_pct"].value is None
    assert m["issue_close_ratio_90d"].value is None
    assert m["median_pr_turnaround_days"].value is None
    assert m["bus_factor_estimate"].value is None
    assert m["days_since_last_release"].value is None


def test_commit_metrics_and_bot_exclusion():
    commits = [commit(d) for d in (1, 2, 3, 10)] + [commit(40), commit(50), commit(80), commit(120)]
    commits += [commit(1, "dependabot[bot]", bot=True)] * 5
    m = compute_metrics(RepoData(as_of=NOW, commits=commits))
    assert m["commits_90d"].value == 7
    assert m["commit_frequency_per_week"].value == pytest.approx(7 / (90 / 7), abs=0.01)
    assert m["days_since_last_commit"].value == 1.0
    # c30 = 4, c60 = 3 -> baseline 1.5 -> (4 - 1.5) / 1.5 = +166% -> capped at +100
    assert m["activity_trend_pct"].value == 100.0


def test_activity_decline():
    commits = [commit(d) for d in (35, 40, 45, 50, 55, 60, 65, 70)] + [commit(5)]
    m = compute_metrics(RepoData(as_of=NOW, commits=commits))
    # c30 = 1, c60 = 8 -> baseline 4 -> -75%
    assert m["activity_trend_pct"].value == -75.0


def test_contributor_concentration_and_bus_factor():
    commits = [commit(i + 1, "alice") for i in range(6)] + [commit(10, "bob"), commit(11, "bob"),
                                                            commit(12, "carol"), commit(13, "dave")]
    m = compute_metrics(RepoData(as_of=NOW, commits=commits))
    assert m["contributors_90d"].value == 4
    assert m["top_contributor_share"].value == 0.6
    assert m["bus_factor_estimate"].value == 1  # alice alone >= 50%


def test_bus_factor_two():
    commits = [commit(1, "a")] * 4 + [commit(1, "b")] * 3 + [commit(1, "c")] * 3
    assert compute_metrics(RepoData(as_of=NOW, commits=commits))["bus_factor_estimate"].value == 2


def test_active_weeks_ratio():
    commits = [commit(1), commit(8), commit(15), commit(16)]  # weeks 0, 1, 2
    assert compute_metrics(RepoData(as_of=NOW, commits=commits))["active_weeks_ratio"].value == round(3 / 13, 2)


def test_issue_metrics():
    issues = [
        {"state": "open", "created_at": ago(10), "closed_at": None},
        {"state": "open", "created_at": ago(100), "closed_at": None},
        {"state": "open", "created_at": ago(200), "closed_at": None},
        {"state": "closed", "created_at": ago(20), "closed_at": ago(18)},
        {"state": "closed", "created_at": ago(400), "closed_at": ago(30)},
    ]
    m = compute_metrics(RepoData(as_of=NOW, issues=issues))
    assert m["open_issues"].value == 3
    assert m["issues_opened_90d"].value == 2
    assert m["issues_closed_90d"].value == 2
    assert m["issue_close_ratio_90d"].value == 1.0
    assert m["median_open_issue_age_days"].value == 100.0
    assert m["median_issue_resolution_days"].value == pytest.approx((2 + 370) / 2)


def test_pull_request_metrics():
    pulls = []
    for i, turnaround in enumerate([1, 2, 3]):  # merged in last 30 days
        pulls.append({"state": "closed", "created_at": ago(5 + i + turnaround), "updated_at": ago(5 + i),
                      "merged_at": ago(5 + i), "additions": 100, "deletions": 20 * i})
    for i, turnaround in enumerate([4, 5, 6]):  # merged 30-90 days ago
        pulls.append({"state": "closed", "created_at": ago(40 + i + turnaround), "updated_at": ago(40 + i),
                      "merged_at": ago(40 + i), "additions": None, "deletions": None})
    pulls.append({"state": "open", "created_at": ago(60), "updated_at": ago(45), "merged_at": None})
    pulls.append({"state": "open", "created_at": ago(3), "updated_at": ago(1), "merged_at": None})
    m = compute_metrics(RepoData(as_of=NOW, pulls=pulls))
    assert m["prs_merged_90d"].value == 6
    assert m["median_pr_turnaround_days"].value == 3.5
    assert m["pr_turnaround_trend_pct"].value == pytest.approx((2 - 5) / 5 * 100)
    assert m["stale_open_pr_ratio"].value == 0.5
    assert m["median_pr_size_lines"].value == 120


def test_release_metrics():
    releases = [{"published_at": ago(30), "prerelease": False}, {"published_at": ago(400), "prerelease": False}]
    m = compute_metrics(RepoData(as_of=NOW, releases=releases))
    assert m["releases_365d"].value == 1
    assert m["days_since_last_release"].value == 30.0


def test_future_data_is_ignored():
    m = compute_metrics(RepoData(as_of=NOW, commits=[commit(-5), commit(2)]))
    assert m["commits_90d"].value == 1


def test_weekly_activity_shape_and_buckets():
    data = RepoData(as_of=NOW, commits=[commit(1), commit(2), commit(8), commit(400)],
                    pulls=[{"state": "closed", "created_at": ago(3), "merged_at": ago(1)}],
                    issues=[{"state": "open", "created_at": ago(9), "closed_at": None}])
    frame = weekly_activity(data)
    assert len(frame) == 52
    assert frame.iloc[-1]["commits"] == 2 and frame.iloc[-2]["commits"] == 1
    assert frame["commits"].sum() == 3  # the 400-day-old commit is outside 52 weeks
    assert frame.iloc[-1]["prs_merged"] == 1 and frame.iloc[-2]["issues_opened"] == 1
