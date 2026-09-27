"""Shared FastAPI dependencies. Tests override `get_client_factory` / `get_session_factory` to avoid the network."""

from collections.abc import Callable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal, get_db
from app.models import AnalysisRun, AuditLog, Project
from app.services.github_client import GitHubClient


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str, **extra):
        self.status_code, self.code, self.message, self.extra = status_code, code, message, extra


def get_client_factory(settings: Settings = Depends(get_settings)) -> Callable[[], GitHubClient]:
    token = settings.github_token.get_secret_value() if settings.github_token else None
    return lambda: GitHubClient(token=token, base_url=settings.github_api_url)


def get_session_factory() -> Callable[[], Session]:
    return SessionLocal


def get_project_or_404(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise APIError(404, "PROJECT_NOT_FOUND", f"Project {project_id} does not exist.")
    return project


def completed_run(db: Session, project: Project, run_id: int | None) -> AnalysisRun:
    query = select(AnalysisRun).where(AnalysisRun.project_id == project.id, AnalysisRun.status == "COMPLETED")
    if run_id is not None:
        query = query.where(AnalysisRun.id == run_id)
    run = db.scalars(query.order_by(AnalysisRun.started_at.desc(), AnalysisRun.id.desc()).limit(1)).first()
    if run is None:
        raise APIError(404, "NO_COMPLETED_ANALYSIS",
                       "No completed analysis for this project yet. Run an analysis first.")
    return run


def audit(db: Session, action: str, entity: str, entity_id: int | None, **detail) -> None:
    db.add(AuditLog(action=action, entity=entity, entity_id=entity_id, detail=detail or None))
