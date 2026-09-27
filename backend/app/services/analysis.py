"""Analysis orchestration: collect → metrics → risk → recommendations → ML → persist.

Runs as a FastAPI background task. It opens its own DB session because the request session is closed once
the 202 response is sent. Any failure marks the run FAILED with a safe error code/message.
"""

import logging
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.time import as_utc, utcnow
from app.engines.metrics import METRIC_DEFINITIONS, RepoData, compute_metrics, weekly_activity
from app.engines.recommendations import generate_recommendations
from app.engines.risk import compute_risk, load_config
from app.ml.anomaly import detect_anomalies
from app.ml.dormancy import predict_dormancy
from app.models import (
    AnalysisRun,
    Commit,
    Contributor,
    Issue,
    Project,
    PullRequest,
    Recommendation,
    Release,
    RepositoryMetric,
    RiskAssessment,
    RiskFactor,
)
from app.services.collector import collect
from app.services.github_client import GitHubClient, GitHubError

log = logging.getLogger("prospect.analysis")


def load_repo_data(db: Session, project: Project, as_of, window_days: int) -> RepoData:
    since = as_of - timedelta(days=window_days)
    commits = [dict(authored_at=as_utc(c.authored_at), author_key=c.author_key, is_bot=c.is_bot)
               for c in db.scalars(select(Commit).where(Commit.project_id == project.id, Commit.authored_at > since))]
    issues = [dict(state=i.state, created_at=as_utc(i.created_at), closed_at=as_utc(i.closed_at))
              for i in db.scalars(select(Issue).where(Issue.project_id == project.id))]
    pulls = [dict(state=p.state, created_at=as_utc(p.created_at), updated_at=as_utc(p.updated_at),
                  merged_at=as_utc(p.merged_at), additions=p.additions, deletions=p.deletions)
             for p in db.scalars(select(PullRequest).where(PullRequest.project_id == project.id))]
    releases = [dict(published_at=as_utc(r.published_at), prerelease=r.prerelease)
                for r in db.scalars(select(Release).where(Release.project_id == project.id))]
    contributors = [dict(login=c.login, contributions=c.contributions, is_bot=c.is_bot)
                    for c in db.scalars(select(Contributor).where(Contributor.project_id == project.id))]
    return RepoData(as_of=as_of, commits=commits, issues=issues, pulls=pulls, releases=releases,
                    contributors=contributors)


def metrics_dict(run: AnalysisRun) -> dict[str, float | None]:
    return {m.key: m.value for m in run.metrics}


def persist_assessment(db: Session, run: AnalysisRun, metric_values: dict[str, float | None], config: dict):
    result = compute_risk(metric_values, config)
    assessment = RiskAssessment(run_id=run.id, risk_score=result.risk_score, health_score=result.health_score,
                                risk_level=result.risk_level, coverage=result.coverage, config_snapshot=config,
                                dimensions=[{k: v for k, v in d.items() if k != "signals"}
                                            for d in result.to_dict()["dimensions"]],
                                engine_version=result.engine_version)
    db.add(assessment)
    db.flush()
    factor_ids = {}
    for s in result.signals:
        factor = RiskFactor(assessment_id=assessment.id, dimension=s.dimension, signal_key=s.key,
                            metric_key=s.metric_key, metric_value=s.metric_value, score=s.score,
                            contribution=s.contribution, severity=s.severity, explanation=s.explanation)
        db.add(factor)
        db.flush()
        factor_ids[s.key] = factor.id
    for rec in generate_recommendations(result):
        db.add(Recommendation(assessment_id=assessment.id, risk_factor_id=factor_ids.get(rec.signal_key),
                              signal_key=rec.signal_key, priority=rec.priority, title=rec.title, detail=rec.detail))
    return result


def execute_run(run_id: int, session_factory: Callable[[], Session],
                client_factory: Callable[[], GitHubClient], settings: Settings, force: bool = False) -> None:
    db = session_factory()
    try:
        run = db.get(AnalysisRun, run_id)
        if run is None:
            return
        project = db.get(Project, run.project_id)
        run.status = "RUNNING"
        db.commit()

        notes: list[str] = []
        last = as_utc(project.last_collected_at)
        fresh = last and utcnow() - last < timedelta(minutes=settings.cache_ttl_minutes)
        if fresh and not force:
            run.used_cache = True
            notes.append(f"Reused data collected at {last.isoformat()} (cache TTL {settings.cache_ttl_minutes} min).")
        else:
            client = client_factory()
            try:
                report = collect(db, project, client, settings)
            finally:
                client.close()
            run.api_calls = report.api_calls
            run.data_truncated = report.truncated
            notes.extend(report.notes)

        as_of = utcnow()
        data = load_repo_data(db, project, as_of, settings.analysis_window_days)
        values = compute_metrics(data)
        for key, mv in values.items():
            db.add(RepositoryMetric(run_id=run.id, key=key, value=mv.value, unit=METRIC_DEFINITIONS[key]["unit"],
                                    note=mv.note))
        db.flush()
        if not data.commits and not data.issues and not data.pulls:
            notes.append("No commits, issues or pull requests found in the analysis window.")

        persist_assessment(db, run, {k: v.value for k, v in values.items()}, load_config(settings.risk_config_path))

        human = [c for c in data.commits if not c["is_bot"]]
        ml_output = {"anomaly": detect_anomalies(weekly_activity(data))}
        try:
            ml_output["dormancy"] = predict_dormancy([c["authored_at"] for c in human],
                                                     [c["author_key"] for c in human], as_of,
                                                     settings.model_path, run.data_truncated)
        except Exception as exc:  # model problems must never break the core analysis
            log.warning("dormancy model failed: %s", exc)
            ml_output["dormancy"] = {"status": "error", "message": "Model could not be evaluated."}
        run.ml_output = ml_output
        run.collection_notes = notes
        run.status = "COMPLETED"
        run.finished_at = utcnow()
        db.commit()
    except GitHubError as exc:
        db.rollback()
        _fail(db, run_id, exc.code, exc.message)
    except Exception:
        log.exception("analysis run %s failed", run_id)
        db.rollback()
        _fail(db, run_id, "INTERNAL_ERROR", "Analysis failed because of an internal error. See server logs.")
    finally:
        db.close()


def _fail(db: Session, run_id: int, code: str, message: str) -> None:
    run = db.get(AnalysisRun, run_id)
    if run:
        run.status, run.error_code, run.error_message, run.finished_at = "FAILED", code, message, utcnow()
        db.commit()
