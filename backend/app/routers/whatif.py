import json
from dataclasses import fields

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Analysis
from ..risk_engine import RepoMetrics, calculate_risk
from ..schemas import AnalysisResult, WhatIfRequest

router = APIRouter(prefix="/api", tags=["whatif"])

_ALLOWED_FIELDS = {f.name for f in fields(RepoMetrics)}


@router.post("/whatif/{analysis_id}", response_model=AnalysisResult)
def what_if(analysis_id: int, payload: WhatIfRequest, db: Session = Depends(get_db)):
    record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    base_metrics = json.loads(record.metrics_json)

    unknown = set(payload.overrides.keys()) - _ALLOWED_FIELDS
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown metric field(s) for simulation: {sorted(unknown)}",
        )

    simulated = dict(base_metrics)
    simulated.update(payload.overrides)
    metrics = RepoMetrics(**simulated)

    risk_result = calculate_risk(metrics)

    return AnalysisResult(
        id=record.id,
        repo_full_name=record.repo_full_name,
        repo_url=record.repo_url,
        description=record.description,
        primary_language=record.primary_language,
        stars=record.stars,
        forks=record.forks,
        risk_score=risk_result.risk_score,
        health_score=risk_result.health_score,
        classification=risk_result.classification,
        factors=[f.to_dict() for f in risk_result.factors],
        recommendations=risk_result.recommendations,
        metrics=metrics.to_dict(),
        extra={"base_risk_score": record.risk_score, "base_classification": record.classification},
        is_simulation=True,
        created_at=record.created_at,
    )
