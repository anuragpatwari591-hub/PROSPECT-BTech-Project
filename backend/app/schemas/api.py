"""Pydantic request/response models — these define and validate the REST contract (and the OpenAPI docs)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    repository_url: str = Field(min_length=3, max_length=300, examples=["https://github.com/pallets/flask"])


class RiskSummary(BaseModel):
    run_id: int
    analyzed_at: datetime | None
    risk_score: float
    health_score: float
    risk_level: str


class ProjectOut(ORM):
    id: int
    name: str
    owner: str
    repo: str
    url: str
    description: str | None
    stars: int | None
    forks: int | None
    is_archived: bool
    default_branch: str | None
    last_collected_at: datetime | None
    created_at: datetime
    latest: RiskSummary | None = None
    active_run: "RunOut | None" = None


class RunOut(ORM):
    id: int
    project_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None
    used_cache: bool
    api_calls: int
    data_truncated: bool
    collection_notes: list[str] | None


class MetricOut(BaseModel):
    key: str
    name: str
    value: float | None
    unit: str
    note: str | None
    definition: str
    formula: str
    source: str
    interpretation: str
    limitations: str


class MetricsResponse(BaseModel):
    run: RunOut
    metrics: list[MetricOut]


class FactorOut(ORM):
    id: int
    dimension: str
    signal_key: str
    metric_key: str
    metric_value: float | None
    score: float
    contribution: float
    severity: str
    explanation: str


class RecommendationOut(ORM):
    id: int
    risk_factor_id: int | None
    signal_key: str
    priority: str
    title: str
    detail: str


class RiskResponse(BaseModel):
    run: RunOut
    risk_score: float
    health_score: float
    risk_level: str
    coverage: float
    engine_version: str
    dimensions: list[dict]
    factors: list[FactorOut]
    top_factors: list[FactorOut]
    ml: dict | None
    disclaimer: str


class HistoryPoint(BaseModel):
    run_id: int
    analyzed_at: datetime
    risk_score: float
    health_score: float
    risk_level: str
    key_metrics: dict[str, float | None]


class HistoryResponse(BaseModel):
    points: list[HistoryPoint]
    changes: dict[str, dict | None]


class SimulationRequest(BaseModel):
    overrides: dict[str, float] = Field(examples=[{"median_pr_turnaround_days": 2, "issue_close_ratio_90d": 1.0}])
    run_id: int | None = None


class SimulationResponse(BaseModel):
    label: str
    run_id: int
    scenario_id: int
    baseline_score: float
    simulated_score: float
    difference: float
    baseline_level: str
    simulated_level: str
    applied: dict[str, float]
    dimensions: list[dict]


ProjectOut.model_rebuild()
