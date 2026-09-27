import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import github_client
from ..database import get_db
from ..models import Analysis
from ..risk_engine import calculate_risk
from ..schemas import AnalysisResult, AnalyzeRequest

router = APIRouter(prefix="/api", tags=["analyze"])


def _serialize_result(
    repo_full_name, repo_url, extra, metrics, risk_result, record_id=None,
    is_simulation=False, created_at=None,
):
    return AnalysisResult(
        id=record_id,
        repo_full_name=repo_full_name,
        repo_url=repo_url,
        description=extra.get("description"),
        primary_language=extra.get("language"),
        stars=extra.get("stars", 0),
        forks=extra.get("forks", 0),
        risk_score=risk_result.risk_score,
        health_score=risk_result.health_score,
        classification=risk_result.classification,
        factors=[f.to_dict() for f in risk_result.factors],
        recommendations=risk_result.recommendations,
        metrics=metrics.to_dict(),
        extra=extra,
        is_simulation=is_simulation,
        created_at=created_at,
    ).model_dump()


@router.post("/analyze", response_model=AnalysisResult)
def analyze_repo(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    try:
        owner, repo = github_client.parse_repo_url(payload.repo_url)
    except github_client.InvalidRepoUrlError as e:
        raise HTTPException(status_code=422, detail=str(e))

    client = github_client.GitHubClient()
    try:
        extra, metrics = github_client.build_metrics(client, owner, repo)
    except github_client.RepoNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"GitHub repository '{owner}/{repo}' was not found."
        )
    except github_client.RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except github_client.GitHubError as e:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {e}")

    risk_result = calculate_risk(metrics)

    record = Analysis(
        repo_full_name=extra.get("full_name") or f"{owner}/{repo}",
        repo_url=extra.get("html_url") or payload.repo_url,
        description=extra.get("description"),
        primary_language=extra.get("language"),
        stars=extra.get("stars", 0),
        forks=extra.get("forks", 0),
        risk_score=risk_result.risk_score,
        health_score=risk_result.health_score,
        classification=risk_result.classification,
        metrics_json=json.dumps(metrics.to_dict()),
        factors_json=json.dumps([f.to_dict() for f in risk_result.factors]),
        recommendations_json=json.dumps(risk_result.recommendations),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return _serialize_result(
        record.repo_full_name,
        record.repo_url,
        extra,
        metrics,
        risk_result,
        record_id=record.id,
        created_at=record.created_at,
    )
