"""Health check, metric definitions, risk model configuration and ML model card."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.api.deps import APIError
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.engines.metrics import METRIC_DEFINITIONS
from app.engines.risk import load_config
from app.engines.simulator import SIMULATABLE_METRICS

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", summary="Liveness + database connectivity")
def health(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise APIError(503, "DATABASE_UNAVAILABLE", "Database is not reachable.") from exc
    # Reports only WHETHER a token is configured — never the token itself.
    return {"status": "ok", "version": __version__, "environment": settings.environment,
            "github_token_configured": settings.github_token is not None}


@router.get("/metrics/definitions", summary="Definition, formula and limitations of every metric")
def metric_definitions():
    return METRIC_DEFINITIONS


@router.get("/risk-model", summary="Active risk model configuration (weights, thresholds, levels)")
def risk_model(settings: Settings = Depends(get_settings)):
    return {"config": load_config(settings.risk_config_path),
            "simulatable_metrics": {k: {"min": lo, "max": hi} for k, (lo, hi) in SIMULATABLE_METRICS.items()}}


@router.get("/ml/model-card", summary="Measured results of the experimental dormancy model")
def model_card():
    path = Path(__file__).resolve().parents[2] / "ml" / "artifacts" / "metrics.json"
    if not path.exists():
        return {"status": "model_unavailable"}
    return {"status": "ok", **json.loads(path.read_text())}
