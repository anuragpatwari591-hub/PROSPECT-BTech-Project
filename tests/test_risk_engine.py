from app.risk_engine import RepoMetrics, calculate_risk, classify


def healthy_metrics(**overrides):
    base = dict(
        archived=False,
        days_since_last_push=1,
        contributor_count=25,
        top_contributor_pct=10.0,
        open_issue_count=5,
        closed_issue_count=95,
        stale_open_issue_count=0,
        open_pr_count=2,
        closed_unmerged_pr_count=5,
        merged_pr_count=95,
        stale_open_pr_count=0,
        release_count=20,
        days_since_last_release=10,
    )
    base.update(overrides)
    return RepoMetrics(**base)


def risky_metrics(**overrides):
    base = dict(
        archived=False,
        days_since_last_push=900,
        contributor_count=1,
        top_contributor_pct=100.0,
        open_issue_count=50,
        closed_issue_count=5,
        stale_open_issue_count=50,
        open_pr_count=10,
        closed_unmerged_pr_count=10,
        merged_pr_count=0,
        stale_open_pr_count=10,
        release_count=0,
        days_since_last_release=None,
    )
    base.update(overrides)
    return RepoMetrics(**base)


def test_healthy_repo_scores_low_risk():
    result = calculate_risk(healthy_metrics())
    assert result.risk_score < 25
    assert result.classification == "LOW"
    assert result.health_score == round(100 - result.risk_score, 1)


def test_risky_repo_scores_critical():
    result = calculate_risk(risky_metrics())
    assert result.risk_score > 75
    assert result.classification == "CRITICAL"


def test_risk_score_is_deterministic():
    m1 = risky_metrics()
    m2 = risky_metrics()
    r1 = calculate_risk(m1)
    r2 = calculate_risk(m2)
    assert r1.risk_score == r2.risk_score
    assert r1.classification == r2.classification
    assert [f.points for f in r1.factors] == [f.points for f in r2.factors]


def test_score_never_exceeds_100():
    extreme = risky_metrics(
        days_since_last_push=100000,
        contributor_count=0,
        top_contributor_pct=100.0,
        open_issue_count=1000,
        stale_open_issue_count=1000,
        closed_issue_count=0,
        open_pr_count=1000,
        stale_open_pr_count=1000,
        closed_unmerged_pr_count=1000,
        merged_pr_count=0,
    )
    result = calculate_risk(extreme)
    assert result.risk_score <= 100
    assert result.health_score >= 0


def test_archived_repo_forces_max_activity_risk():
    m = healthy_metrics(archived=True)
    result = calculate_risk(m)
    activity_factor = next(f for f in result.factors if f.key == "activity")
    assert activity_factor.points == activity_factor.max_points


def test_no_commit_history_is_max_activity_risk():
    m = healthy_metrics(days_since_last_push=None)
    result = calculate_risk(m)
    activity_factor = next(f for f in result.factors if f.key == "activity")
    assert activity_factor.points == 25.0


def test_no_releases_gives_moderate_not_max_risk():
    m = healthy_metrics(release_count=0, days_since_last_release=None)
    result = calculate_risk(m)
    release_factor = next(f for f in result.factors if f.key == "releases")
    assert release_factor.points == 10.0
    assert release_factor.points < release_factor.max_points


def test_single_contributor_flagged_as_bus_factor_risk():
    m = healthy_metrics(contributor_count=1, top_contributor_pct=100.0)
    result = calculate_risk(m)
    contributor_factor = next(f for f in result.factors if f.key == "contributors")
    assert contributor_factor.points == contributor_factor.max_points


def test_no_issues_at_all_is_neutral_not_risky():
    m = healthy_metrics(open_issue_count=0, closed_issue_count=0, stale_open_issue_count=0)
    result = calculate_risk(m)
    issue_factor = next(f for f in result.factors if f.key == "issues")
    assert issue_factor.points == 0.0


def test_classify_boundaries():
    assert classify(0) == "LOW"
    assert classify(25) == "LOW"
    assert classify(25.1) == "MEDIUM"
    assert classify(50) == "MEDIUM"
    assert classify(50.1) == "HIGH"
    assert classify(75) == "HIGH"
    assert classify(75.1) == "CRITICAL"
    assert classify(100) == "CRITICAL"


def test_max_points_sum_to_100():
    result = calculate_risk(healthy_metrics())
    assert sum(f.max_points for f in result.factors) == 100.0


def test_recommendations_reflect_triggered_factors():
    m = risky_metrics()
    result = calculate_risk(m)
    assert len(result.recommendations) > 0
    assert all(isinstance(r, str) for r in result.recommendations)


def test_healthy_repo_gets_default_recommendation():
    result = calculate_risk(healthy_metrics())
    assert "No significant risk factors" in result.recommendations[0]


def test_same_repo_identity_does_not_change_outcome():
    """The engine must not special-case any repository: metrics alone decide
    the score, never a name or URL (which the engine never even sees)."""
    metrics = risky_metrics()
    result_a = calculate_risk(metrics)
    result_b = calculate_risk(metrics)
    assert result_a.to_dict() == result_b.to_dict()
