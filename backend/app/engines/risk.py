"""Baseline Risk Engine — transparent weighted aggregation.

overall_risk = Σ_d  w'_d × dimension_score_d          (w'_d = weights renormalised over dimensions with data)
dimension_score_d = mean(signal scores available in d)
contribution(signal) = w'_d × signal_score / n_available_signals_in_d

Because the model is linear, the contributions of all signals add up EXACTLY to the overall score — that is
what makes every point of the score explainable. Health score = 100 − risk score.
"""

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.engines.risk_config import DEFAULT_RISK_CONFIG

ENGINE_VERSION = "rules-1.0"


class RiskConfigError(ValueError):
    pass


@dataclass
class SignalResult:
    key: str
    dimension: str
    label: str
    metric_key: str
    metric_value: float | None
    score: float
    contribution: float
    severity: str
    explanation: str


@dataclass
class DimensionResult:
    key: str
    label: str
    weight: float
    effective_weight: float
    score: float | None
    contribution: float
    signals: list[SignalResult] = field(default_factory=list)
    status: str = "scored"  # scored | not_applicable


@dataclass
class RiskResult:
    risk_score: float
    health_score: float
    risk_level: str
    coverage: float
    dimensions: list[DimensionResult]
    engine_version: str = ENGINE_VERSION

    @property
    def signals(self) -> list[SignalResult]:
        return [s for d in self.dimensions for s in d.signals]

    def top_factors(self, n: int = 5) -> list[SignalResult]:
        return sorted((s for s in self.signals if s.contribution > 0), key=lambda s: s.contribution, reverse=True)[:n]

    def to_dict(self) -> dict:
        return asdict(self)


def validate_config(config: dict) -> dict:
    dims = config.get("dimensions")
    if not isinstance(dims, dict) or not dims:
        raise RiskConfigError("Risk config needs at least one dimension.")
    total = 0.0
    for name, dim in dims.items():
        weight = dim.get("weight")
        if not isinstance(weight, int | float) or weight < 0:
            raise RiskConfigError(f"Dimension '{name}' needs a non-negative weight.")
        total += weight
        for sname, sig in dim.get("signals", {}).items():
            pts = sig.get("points")
            if not pts or len(pts) < 2 or any(len(p) != 2 for p in pts):
                raise RiskConfigError(f"Signal '{name}.{sname}' needs at least two [value, score] points.")
            if any(not 0 <= p[1] <= 100 for p in pts):
                raise RiskConfigError(f"Signal '{name}.{sname}' scores must be within 0–100.")
    if total <= 0:
        raise RiskConfigError("Dimension weights must sum to a positive number.")
    levels = config.get("levels", {})
    if [levels.get(k) for k in ("LOW", "MEDIUM", "HIGH", "CRITICAL")] != sorted(levels.values()):
        raise RiskConfigError("Level thresholds must be increasing LOW < MEDIUM < HIGH < CRITICAL.")
    return config


def load_config(path: str | None = None) -> dict:
    if not path:
        return copy.deepcopy(DEFAULT_RISK_CONFIG)
    return validate_config(json.loads(Path(path).read_text(encoding="utf-8")))


def interpolate(value: float, points: list[list[float]]) -> float:
    pts = sorted(points, key=lambda p: p[0])
    if value <= pts[0][0]:
        return float(pts[0][1])
    if value >= pts[-1][0]:
        return float(pts[-1][1])
    for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
        if x0 <= value <= x1:
            return float(y0 + (y1 - y0) * (value - x0) / (x1 - x0))
    return float(pts[-1][1])  # pragma: no cover


def severity_for(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def level_for(score: float, levels: dict) -> str:
    level = "LOW"
    for name in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        if score >= levels[name]:
            level = name
    return level


def _fmt(value: float | None) -> str:
    if value is None:
        return "not available"
    return f"{value:.0f}" if abs(value) >= 100 or float(value).is_integer() else f"{value:.2f}"


def _explain(label: str, metric_key: str, value: float | None, score: float, points: list, missing: bool) -> str:
    if missing:
        return f"{label}: no data, treated as maximum risk for this signal."
    lo, hi = sorted(points, key=lambda p: p[1])[0], sorted(points, key=lambda p: p[1])[-1]
    return (f"{label} is {_fmt(value)} ({metric_key}). Risk for this signal is 0 at {_fmt(lo[0])} and 100 at "
            f"{_fmt(hi[0])}, so it scores {score:.0f}/100.")


def compute_risk(metrics: dict[str, float | None], config: dict | None = None) -> RiskResult:
    config = validate_config(config or DEFAULT_RISK_CONFIG)
    staged: list[tuple[str, dict, list[tuple[str, dict, float | None, float, bool]]]] = []
    for dkey, dim in config["dimensions"].items():
        scored = []
        for skey, sig in dim["signals"].items():
            value = metrics.get(sig["metric"])
            if value is None:
                if "missing_score" in sig:
                    scored.append((skey, sig, None, float(sig["missing_score"]), True))
                continue
            scored.append((skey, sig, float(value), interpolate(float(value), sig["points"]), False))
        staged.append((dkey, dim, scored))

    active_weight = sum(dim["weight"] for _, dim, scored in staged if scored)
    total_weight = sum(dim["weight"] for _, dim, _ in staged)
    dimensions: list[DimensionResult] = []
    overall = 0.0
    for dkey, dim, scored in staged:
        if not scored or active_weight == 0:
            dimensions.append(DimensionResult(dkey, dim["label"], dim["weight"], 0.0, None, 0.0,
                                              status="not_applicable"))
            continue
        eff = dim["weight"] / active_weight
        signals = []
        for skey, sig, value, score, missing in scored:
            contribution = eff * score / len(scored)
            signals.append(SignalResult(
                key=f"{dkey}.{skey}", dimension=dkey, label=sig["label"], metric_key=sig["metric"],
                metric_value=value, score=round(score, 1), contribution=round(contribution, 2),
                severity=severity_for(score), explanation=_explain(sig["label"], sig["metric"], value, score,
                                                                   sig["points"], missing)))
        dim_score = sum(s[3] for s in scored) / len(scored)
        overall += eff * dim_score
        dimensions.append(DimensionResult(dkey, dim["label"], dim["weight"], round(eff, 4), round(dim_score, 1),
                                          round(eff * dim_score, 2), signals))
    risk = round(min(100.0, max(0.0, overall)), 1)
    coverage = round(active_weight / total_weight, 3) if total_weight else 0.0
    return RiskResult(risk_score=risk, health_score=round(100 - risk, 1),
                      risk_level=level_for(risk, config["levels"]), coverage=coverage, dimensions=dimensions)
