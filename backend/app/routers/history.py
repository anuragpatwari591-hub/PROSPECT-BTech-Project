import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Analysis
from ..schemas import AnalysisResult, AnalysisSummary

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history", response_model=list[AnalysisSummary])
def list_history(limit: int = 50, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    records = (
        db.query(Analysis).order_by(desc(Analysis.created_at)).limit(limit).all()
    )
    return records


@router.get("/history/{analysis_id}", response_model=AnalysisResult)
def get_history_item(analysis_id: int, db: Session = Depends(get_db)):
    record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    metrics = json.loads(record.metrics_json)
    factors = json.loads(record.factors_json)
    recommendations = json.loads(record.recommendations_json)

    return AnalysisResult(
        id=record.id,
        repo_full_name=record.repo_full_name,
        repo_url=record.repo_url,
        description=record.description,
        primary_language=record.primary_language,
        stars=record.stars,
        forks=record.forks,
        risk_score=record.risk_score,
        health_score=record.health_score,
        classification=record.classification,
        factors=factors,
        recommendations=recommendations,
        metrics=metrics,
        extra={},
        created_at=record.created_at,
    )


@router.delete("/history/{analysis_id}")
def delete_history_item(analysis_id: int, db: Session = Depends(get_db)):
    record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    db.delete(record)
    db.commit()
    return {"deleted": analysis_id}
