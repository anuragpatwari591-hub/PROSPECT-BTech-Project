from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repo URL, e.g. https://github.com/owner/repo")


class RiskFactorSchema(BaseModel):
    key: str
    label: str
    points: float
    max_points: float
    pct_of_max: float
    reasons: List[str]


class AnalysisResult(BaseModel):
    id: Optional[int] = None
    repo_full_name: str
    repo_url: str
    description: Optional[str] = None
    primary_language: Optional[str] = None
    stars: int = 0
    forks: int = 0

    risk_score: float
    health_score: float
    classification: str
    factors: List[RiskFactorSchema]
    recommendations: List[str]

    metrics: dict
    extra: dict = {}

    is_simulation: bool = False
    created_at: Optional[datetime] = None


class AnalysisSummary(BaseModel):
    id: int
    repo_full_name: str
    repo_url: str
    risk_score: float
    health_score: float
    classification: str
    created_at: datetime


class WhatIfRequest(BaseModel):
    overrides: dict = Field(
        default_factory=dict,
        description="Partial RepoMetrics field overrides, e.g. "
        "{'contributor_count': 8, 'days_since_last_push': 2}",
    )
