import copy

import pytest

from app.engines.recommendations import RULES, generate_recommendations
from app.engines.risk import (
    RiskConfigError,
    compute_risk,
    interpolate,
    level_for,
    load_config,
    severity_for,
    validate_config,
)
from app.engines.risk_config import DEFAULT_RISK_CONFIG
from app.engines.simulator import SIMULATABLE_METRICS, SimulationError, simulate

HEALTHY = dict(days_since_last_commit=1, activity_trend_pct=10, active_weeks_ratio=1.0, issue_close_ratio_90d=1.2,
               median_open_issue_age_days=10, median_pr_turnaround_days=0.5, pr_turnaround_trend_pct=-10,
               stale_open_pr_ratio=0.0, median_pr_size_lines=80, top_contributor_share=0.2,
               bus_factor_estimate=5, contributors_90d=12, days_since_last_release=20)
UNHEALTHY = dict(days_since_last_commit=200, activity_trend_pct=-100, active_weeks_ratio=0.0, issue_close_ratio_90d=0.1,
                 median_open_issue_age_days=900, median_pr_turnaround_days=30, pr_turnaround_trend_pct=300,
                 stale_open_pr_ratio=1.0, median_pr_size_lines=5000, top_contributor_share=1.0,
                 bus_factor_estimate=1, contributors_90d=1, days_since_last_release=1000)


def test_interpolation_increasing_decreasing_and_clamping():
    assert interpolate(4, [[1, 0], [4, 50], [14, 100]]) == 50
    assert interpolate(9, [[1, 0], [4, 50], [14, 100]]) == 75
    assert interpolate(-3, [[1, 0], [14, 100]]) == 0
    assert interpolate(99, [[1, 0], [14, 100]]) == 100
    assert interpolate(0.65, [[1.0, 0], [0.3, 100]]) == pytest.approx(50)  # decreasing risk with value
    assert interpolate(2, [[1, 100], [2, 60], [3, 30], [4, 0]]) == 60


def test_healthy_and_unhealthy_extremes():
    good, bad = compute_risk(HEALTHY), compute_risk(UNHEALTHY)
    assert good.risk_score == 0 and good.risk_level == "LOW" and good.health_score == 100
    assert bad.risk_score == 100 and bad.risk_level == "CRITICAL" and bad.health_score == 0


def test_contributions_add_up_to_score():
    metrics = {k: (HEALTHY[k] + UNHEALTHY[k]) / 2 for k in HEALTHY}
    result = compute_risk(metrics)
    assert 0 < result.risk_score < 100
    assert sum(s.contribution for s in result.signals) == pytest.approx(result.risk_score, abs=0.1)
    assert sum(d.contribution for d in result.dimensions) == pytest.approx(result.risk_score, abs=0.1)


def test_missing_dimension_is_excluded_and_weights_renormalised():
    metrics = dict(UNHEALTHY, days_since_last_release=None)
    result = compute_risk(metrics)
    releases = next(d for d in result.dimensions if d.key == "releases")
    assert releases.status == "not_applicable" and releases.score is None
    assert result.coverage == pytest.approx(0.85)
    assert result.risk_score == 100  # renormalised: other dimensions still at 100
    assert sum(d.effective_weight for d in result.dimensions) == pytest.approx(1.0, abs=1e-3)


def test_missing_recency_counts_as_maximum_risk():
    result = compute_risk({"days_since_last_commit": None})
    signal = next(s for s in result.signals if s.key == "activity.recency")
    assert signal.score == 100 and "no data" in signal.explanation


def test_all_missing_gives_zero_coverage_score():
    result = compute_risk({})
    assert result.coverage == pytest.approx(0.25)  # only the recency missing_score applies
    assert result.risk_score == 100


@pytest.mark.parametrize("score,level", [(0, "LOW"), (24.9, "LOW"), (25, "MEDIUM"), (50, "HIGH"),
                                         (74.9, "HIGH"), (75, "CRITICAL"), (100, "CRITICAL")])
def test_levels(score, level):
    assert level_for(score, DEFAULT_RISK_CONFIG["levels"]) == level


def test_severity_bands():
    assert [severity_for(x) for x in (0, 30, 60, 90)] == ["low", "medium", "high", "critical"]


def test_weights_are_configurable():
    config = copy.deepcopy(DEFAULT_RISK_CONFIG)
    for name, dim in config["dimensions"].items():
        dim["weight"] = 1.0 if name == "contributors" else 0.0
    metrics = dict(HEALTHY, top_contributor_share=1.0, bus_factor_estimate=1, contributors_90d=1)
    assert compute_risk(metrics, config).risk_score == 100
    assert compute_risk(metrics).risk_score == pytest.approx(20)


@pytest.mark.parametrize("mutate", [
    lambda c: c.update(dimensions={}),
    lambda c: c["dimensions"]["issues"].update(weight=-1),
    lambda c: c["dimensions"]["issues"]["signals"]["close_ratio"].update(points=[[1, 0]]),
    lambda c: c["dimensions"]["issues"]["signals"]["close_ratio"].update(points=[[1, 0], [2, 150]]),
    lambda c: c.update(levels={"LOW": 0, "MEDIUM": 60, "HIGH": 50, "CRITICAL": 75}),
    lambda c: [d.update(weight=0) for d in c["dimensions"].values()],
])
def test_invalid_config_rejected(mutate):
    config = copy.deepcopy(DEFAULT_RISK_CONFIG)
    mutate(config)
    with pytest.raises(RiskConfigError):
        validate_config(config)


def test_load_config_from_file(tmp_path):
    path = tmp_path / "risk.json"
    import json
    path.write_text(json.dumps(DEFAULT_RISK_CONFIG))
    assert load_config(str(path)) == DEFAULT_RISK_CONFIG
    assert load_config(None) == DEFAULT_RISK_CONFIG


def test_every_signal_has_a_recommendation_rule():
    signal_keys = {f"{d}.{s}" for d, dim in DEFAULT_RISK_CONFIG["dimensions"].items() for s in dim["signals"]}
    assert signal_keys == set(RULES)


def test_recommendations_reference_triggering_factor_and_priority():
    recs = generate_recommendations(compute_risk(UNHEALTHY))
    assert {r.signal_key for r in recs} == set(RULES)
    assert all(r.priority == "HIGH" for r in recs)
    assert generate_recommendations(compute_risk(HEALTHY)) == []
    medium = compute_risk(dict(HEALTHY, median_pr_turnaround_days=6))
    recs = generate_recommendations(medium)
    assert [(r.signal_key, r.priority) for r in recs] == [("pull_requests.turnaround", "MEDIUM")]
    assert "6 days" in recs[0].detail
    assert "0.4" in generate_recommendations(compute_risk(dict(HEALTHY, issue_close_ratio_90d=0.4)))[0].detail


def test_simulation_improves_score_and_is_labelled():
    metrics = dict(HEALTHY, median_pr_turnaround_days=10, issue_close_ratio_90d=0.4)
    result = simulate(metrics, {"median_pr_turnaround_days": 2, "issue_close_ratio_90d": 1.0})
    assert result.simulated.risk_score < result.baseline.risk_score
    assert result.delta == pytest.approx(result.simulated.risk_score - result.baseline.risk_score, abs=0.05)
    assert result.baseline.risk_score == compute_risk(metrics).risk_score  # baseline untouched


@pytest.mark.parametrize("overrides", [{}, {"open_issues": 3}, {"stale_open_pr_ratio": 1.5},
                                       {"median_pr_turnaround_days": -1}, {"bus_factor_estimate": 0}])
def test_simulation_rejects_invalid_overrides(overrides):
    with pytest.raises(SimulationError):
        simulate(HEALTHY, overrides)


def test_simulatable_metrics_are_all_risk_inputs():
    used = {sig["metric"] for dim in DEFAULT_RISK_CONFIG["dimensions"].values() for sig in dim["signals"].values()}
    assert set(SIMULATABLE_METRICS) == used
