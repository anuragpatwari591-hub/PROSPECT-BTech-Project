"""Project, analysis, metrics, risk, history, simulation and report endpoints."""

from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    APIError,
    audit,
    completed_run,
    get_client_factory,
    get_project_or_404,
    get_session_factory,
)
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.time import as_utc, utcnow
from app.engines.metrics import METRIC_DEFINITIONS, weekly_activity
from app.engines.risk import load_config
from app.engines.simulator import LABEL, SimulationError, simulate
from app.models import AnalysisRun, Commit, Contributor, Project, RiskAssessment, Scenario
from app.schemas.api import (
    FactorOut,
    HistoryPoint,
    HistoryResponse,
    MetricOut,
    MetricsResponse,
    ProjectCreate,
    ProjectOut,
    RecommendationOut,
    RiskResponse,
    RiskSummary,
    RunOut,
    SimulationRequest,
    SimulationResponse,
)
from app.services.analysis import execute_run, load_repo_data, metrics_dict
from app.services.github_client import parse_repo_url
from app.services.report import build_report

router = APIRouter(prefix="/api/projects", tags=["projects"])

DISCLAIMER = ("Rule-based heuristic score. Weights and thresholds are configurable defaults and have not been "
              "empirically validated; use it to prioritise investigation, not as a verdict.")
KEY_METRICS = ["commits_90d", "open_issues", "median_pr_turnaround_days", "contributors_90d",
               "top_contributor_share", "activity_trend_pct"]


def _latest_summary(db: Session, project: Project) -> RiskSummary | None:
    row = db.execute(
        select(AnalysisRun, RiskAssessment).join(RiskAssessment, RiskAssessment.run_id == AnalysisRun.id)
        .where(AnalysisRun.project_id == project.id, AnalysisRun.status == "COMPLETED")
        .order_by(AnalysisRun.started_at.desc(), AnalysisRun.id.desc()).limit(1)).first()
    if not row:
        return None
    run, a = row
    return RiskSummary(run_id=run.id, analyzed_at=run.finished_at, risk_score=a.risk_score,
                       health_score=a.health_score, risk_level=a.risk_level)


def _active_run(db: Session, project: Project) -> AnalysisRun | None:
    return db.scalars(select(AnalysisRun).where(AnalysisRun.project_id == project.id,
                                                AnalysisRun.status.in_(("PENDING", "RUNNING")))
                      .order_by(AnalysisRun.id.desc()).limit(1)).first()


def _project_out(db: Session, project: Project) -> ProjectOut:
    out = ProjectOut.model_validate(project)
    out.latest = _latest_summary(db, project)
    active = _active_run(db, project)
    out.active_run = RunOut.model_validate(active) if active else None
    return out


@router.post("", response_model=ProjectOut, status_code=201, summary="Register a GitHub repository")
def create_project(body: ProjectCreate, db: Session = Depends(get_db), client_factory=Depends(get_client_factory)):
    owner, repo = parse_repo_url(body.repository_url)
    existing = db.scalars(select(Project).where(func.lower(Project.owner) == owner.lower(),
                                                func.lower(Project.repo) == repo.lower())).first()
    if existing:
        raise APIError(409, "PROJECT_EXISTS", "This repository is already registered.", project_id=existing.id)
    with client_factory() as client:
        meta = client.get_repository(owner, repo)  # confirms the repository exists and is public
    full = meta.get("full_name") or f"{owner}/{repo}"
    owner, repo = full.split("/", 1)
    project = Project(name=full, owner=owner, repo=repo, url=f"https://github.com/{full}",
                      description=(meta.get("description") or "")[:2000] or None,
                      stars=meta.get("stargazers_count"), forks=meta.get("forks_count"),
                      is_archived=bool(meta.get("archived")), default_branch=meta.get("default_branch"))
    db.add(project)
    db.flush()
    audit(db, "project_created", "project", project.id, repository=full)
    db.commit()
    return _project_out(db, project)


@router.get("", response_model=list[ProjectOut], summary="List projects with their latest risk")
def list_projects(db: Session = Depends(get_db)):
    return [_project_out(db, p) for p in db.scalars(select(Project).order_by(Project.created_at.desc()))]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: Project = Depends(get_project_or_404), db: Session = Depends(get_db)):
    return _project_out(db, project)


@router.delete("/{project_id}", status_code=204, summary="Delete a project and all its analyses")
def delete_project(project: Project = Depends(get_project_or_404), db: Session = Depends(get_db)):
    audit(db, "project_deleted", "project", project.id, repository=project.name)
    db.delete(project)
    db.commit()
    return Response(status_code=204)


@router.post("/{project_id}/analyze", response_model=RunOut, status_code=202,
             summary="Start an analysis run (collect from GitHub, compute metrics and risk)")
def analyze(background: BackgroundTasks, force: bool = Query(False, description="Ignore cached data"),
            project: Project = Depends(get_project_or_404), db: Session = Depends(get_db),
            client_factory=Depends(get_client_factory), session_factory=Depends(get_session_factory),
            settings: Settings = Depends(get_settings)):
    active = _active_run(db, project)
    if active and utcnow() - as_utc(active.started_at) < timedelta(minutes=15):
        raise APIError(409, "ANALYSIS_IN_PROGRESS", "An analysis is already running for this project.",
                       run_id=active.id)
    if active:  # a run stuck for > 15 minutes (e.g. server restart) is marked failed
        active.status, active.error_code, active.error_message = "FAILED", "STALE_RUN", "Run did not finish."
    run = AnalysisRun(project_id=project.id, status="PENDING")
    db.add(run)
    db.flush()
    audit(db, "analysis_requested", "analysis_run", run.id, project_id=project.id, force=force)
    db.commit()
    background.add_task(execute_run, run.id, session_factory, client_factory, settings, force)
    return run


@router.get("/{project_id}/runs", response_model=list[RunOut], summary="All analysis runs, newest first")
def list_runs(project: Project = Depends(get_project_or_404), db: Session = Depends(get_db)):
    return db.scalars(select(AnalysisRun).where(AnalysisRun.project_id == project.id)
                      .order_by(AnalysisRun.id.desc()).limit(100)).all()


@router.get("/{project_id}/runs/{run_id}", response_model=RunOut, summary="Poll the status of a run")
def get_run(run_id: int, project: Project = Depends(get_project_or_404), db: Session = Depends(get_db)):
    run = db.get(AnalysisRun, run_id)
    if run is None or run.project_id != project.id:
        raise APIError(404, "RUN_NOT_FOUND", f"Run {run_id} does not exist for this project.")
    return run


@router.get("/{project_id}/metrics", response_model=MetricsResponse)
def get_metrics(run_id: int | None = None, project: Project = Depends(get_project_or_404),
                db: Session = Depends(get_db)):
    run = completed_run(db, project, run_id)
    metrics = [MetricOut(key=m.key, value=m.value, unit=m.unit, note=m.note,
                         **{k: v for k, v in METRIC_DEFINITIONS[m.key].items() if k != "unit"})
               for m in sorted(run.metrics, key=lambda m: list(METRIC_DEFINITIONS).index(m.key))]
    return MetricsResponse(run=RunOut.model_validate(run), metrics=metrics)


@router.get("/{project_id}/risk", response_model=RiskResponse, summary="Risk score with full explanation")
def get_risk(run_id: int | None = None, project: Project = Depends(get_project_or_404),
             db: Session = Depends(get_db)):
    run = completed_run(db, project, run_id)
    a = run.assessment
    factors = [FactorOut.model_validate(f) for f in a.factors]
    top = sorted((f for f in factors if f.contribution > 0), key=lambda f: f.contribution, reverse=True)[:5]
    return RiskResponse(run=RunOut.model_validate(run), risk_score=a.risk_score, health_score=a.health_score,
                        risk_level=a.risk_level, coverage=a.coverage, engine_version=a.engine_version,
                        dimensions=a.dimensions, factors=factors, top_factors=top, ml=run.ml_output,
                        disclaimer=DISCLAIMER)


@router.get("/{project_id}/recommendations", response_model=list[RecommendationOut])
def get_recommendations(run_id: int | None = None, project: Project = Depends(get_project_or_404),
                        db: Session = Depends(get_db)):
    run = completed_run(db, project, run_id)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(run.assessment.recommendations, key=lambda r: order.get(r.priority, 3))


@router.get("/{project_id}/history", response_model=HistoryResponse, summary="Stored analysis history")
def get_history(project: Project = Depends(get_project_or_404), db: Session = Depends(get_db)):
    runs = db.scalars(select(AnalysisRun).where(AnalysisRun.project_id == project.id,
                                                AnalysisRun.status == "COMPLETED")
                      .order_by(AnalysisRun.started_at.asc(), AnalysisRun.id.asc())).all()
    points = []
    for run in runs:
        values = metrics_dict(run)
        points.append(HistoryPoint(run_id=run.id, analyzed_at=run.finished_at or run.started_at,
                                   risk_score=run.assessment.risk_score, health_score=run.assessment.health_score,
                                   risk_level=run.assessment.risk_level,
                                   key_metrics={k: values.get(k) for k in KEY_METRICS}))
    changes: dict[str, dict | None] = {}
    if points:
        latest = points[-1]
        for label, days in (("7d", 7), ("30d", 30), ("90d", 90)):
            target = as_utc(latest.analyzed_at) - timedelta(days=days)
            older = [p for p in points[:-1] if as_utc(p.analyzed_at) <= target]
            # Only report a change when a real stored run exists at least `days` ago — never interpolate.
            changes[label] = ({"from_run_id": older[-1].run_id, "from_score": older[-1].risk_score,
                               "delta": round(latest.risk_score - older[-1].risk_score, 1)} if older else None)
    return HistoryResponse(points=points, changes=changes)


@router.get("/{project_id}/activity", summary="Weekly activity (52 weeks) from stored data + anomaly output")
def get_activity(project: Project = Depends(get_project_or_404), db: Session = Depends(get_db),
                 settings: Settings = Depends(get_settings)):
    run = completed_run(db, project, None)
    data = load_repo_data(db, project, as_utc(run.finished_at) or utcnow(), settings.analysis_window_days)
    weekly = weekly_activity(data)
    return {"run_id": run.id, "weeks": weekly.to_dict(orient="records"),
            "anomaly": (run.ml_output or {}).get("anomaly")}


@router.get("/{project_id}/contributors", summary="Contributor dependency view")
def get_contributors(project: Project = Depends(get_project_or_404), db: Session = Depends(get_db)):
    run = completed_run(db, project, None)
    since = (as_utc(run.finished_at) or utcnow()) - timedelta(days=90)
    rows = db.execute(select(Commit.author_key, func.count()).where(
        Commit.project_id == project.id, Commit.is_bot.is_(False), Commit.authored_at > since)
        .group_by(Commit.author_key).order_by(func.count().desc())).all()
    total = sum(c for _, c in rows) or 1
    recent = [{"author": a, "commits": c, "share": round(c / total, 3)} for a, c in rows[:15]]
    others = sum(c for _, c in rows[15:])
    all_time = db.scalars(select(Contributor).where(Contributor.project_id == project.id, Contributor.is_bot.is_(False))
                          .order_by(Contributor.contributions.desc()).limit(10)).all()
    return {"run_id": run.id, "window_days": 90, "total_commits": sum(c for _, c in rows),
            "authors": len(rows), "top_authors": recent, "other_commits": others,
            "all_time_top": [{"login": c.login, "contributions": c.contributions} for c in all_time],
            "note": "Commit counts are a proxy for contribution; code review, design and triage are not visible."}


@router.post("/{project_id}/simulate", response_model=SimulationResponse, summary="What-If simulation (estimate)")
def simulate_risk(body: SimulationRequest, project: Project = Depends(get_project_or_404),
                  db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    run = completed_run(db, project, body.run_id)
    config = run.assessment.config_snapshot or load_config(settings.risk_config_path)
    try:
        result = simulate(metrics_dict(run), body.overrides, config)
    except SimulationError as exc:
        raise APIError(422, "INVALID_SIMULATION", str(exc)) from exc
    scenario = Scenario(project_id=project.id, run_id=run.id, overrides=result.applied,
                        baseline_score=result.baseline.risk_score, simulated_score=result.simulated.risk_score)
    db.add(scenario)
    db.commit()
    dims = [{"key": b.key, "label": b.label, "baseline": b.score, "simulated": s.score, "status": s.status}
            for b, s in zip(result.baseline.dimensions, result.simulated.dimensions, strict=True)]
    return SimulationResponse(label=LABEL, run_id=run.id, scenario_id=scenario.id,
                              baseline_score=result.baseline.risk_score, simulated_score=result.simulated.risk_score,
                              difference=result.delta, baseline_level=result.baseline.risk_level,
                              simulated_level=result.simulated.risk_level, applied=result.applied, dimensions=dims)


@router.get("/{project_id}/report", summary="Download a PDF risk report",
            responses={200: {"content": {"application/pdf": {}}}})
def get_report(run_id: int | None = None, project: Project = Depends(get_project_or_404),
               db: Session = Depends(get_db)):
    run = completed_run(db, project, run_id)
    history = get_history(project, db).points
    scenarios = db.scalars(select(Scenario).where(Scenario.run_id == run.id)
                           .order_by(Scenario.created_at.desc()).limit(5)).all()
    pdf = build_report(project, run, history, scenarios, DISCLAIMER)
    audit(db, "report_generated", "analysis_run", run.id, project_id=project.id)
    db.commit()
    filename = f"prospect-{project.owner}-{project.repo}-run{run.id}.pdf".replace(" ", "_")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
