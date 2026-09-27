"""What-If Simulator.

Re-runs the SAME risk engine on a copy of the current metrics with user-supplied overrides. The output is a
SIMULATION / ESTIMATE of how the rule-based score would respond — not a forecast of what will happen.
"""

from dataclasses import dataclass

from app.engines.risk import RiskResult, compute_risk

# metric key -> (minimum, maximum) accepted for simulation
SIMULATABLE_METRICS: dict[str, tuple[float, float]] = {
    "days_since_last_commit": (0, 3650),
    "activity_trend_pct": (-100, 100),
    "active_weeks_ratio": (0, 1),
    "issue_close_ratio_90d": (0, 10),
    "median_open_issue_age_days": (0, 3650),
    "median_pr_turnaround_days": (0, 365),
    "pr_turnaround_trend_pct": (-100, 300),
    "stale_open_pr_ratio": (0, 1),
    "median_pr_size_lines": (0, 100000),
    "top_contributor_share": (0, 1),
    "bus_factor_estimate": (1, 100),
    "contributors_90d": (0, 10000),
    "days_since_last_release": (0, 3650),
}

LABEL = "SIMULATION / ESTIMATE — output of the rule-based model under hypothetical metric values, not a prediction."


class SimulationError(ValueError):
    pass


@dataclass
class SimulationResult:
    baseline: RiskResult
    simulated: RiskResult
    applied: dict[str, float]

    @property
    def delta(self) -> float:
        return round(self.simulated.risk_score - self.baseline.risk_score, 1)


def validate_overrides(overrides: dict[str, float]) -> dict[str, float]:
    clean = {}
    for key, value in overrides.items():
        if key not in SIMULATABLE_METRICS:
            raise SimulationError(f"'{key}' cannot be simulated.")
        low, high = SIMULATABLE_METRICS[key]
        if value is None or not low <= float(value) <= high:
            raise SimulationError(f"'{key}' must be between {low} and {high}.")
        clean[key] = float(value)
    if not clean:
        raise SimulationError("Provide at least one metric to change.")
    return clean


def simulate(metrics: dict[str, float | None], overrides: dict[str, float],
             config: dict | None = None) -> SimulationResult:
    applied = validate_overrides(overrides)
    baseline = compute_risk(metrics, config)
    simulated = compute_risk({**metrics, **applied}, config)
    return SimulationResult(baseline, simulated, applied)
