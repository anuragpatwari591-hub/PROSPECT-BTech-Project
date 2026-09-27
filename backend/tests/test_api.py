"""API + integration tests: fake GitHub → real client → collector → engines → database → REST responses."""

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models import AuditLog, Commit, Issue, PullRequest, Release, RiskFactor


def create(client, url="https://github.com/acme/widget"):
    return client.post("/api/projects", json={"repository_url": url})


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["github_token_configured"] is True


def test_openapi_schema_available(client):
    schema = client.get("/openapi.json").json()
    for path in ["/api/projects", "/api/projects/{project_id}/analyze", "/api/projects/{project_id}/risk",
                 "/api/projects/{project_id}/simulate", "/api/projects/{project_id}/report"]:
        assert path in schema["paths"]
    assert client.get("/docs").status_code == 200


def test_create_and_list_project(client):
    response = create(client)
    assert response.status_code == 201
    project = response.json()
    assert project["name"] == "acme/widget" and project["stars"] == 42 and project["latest"] is None
    assert [p["id"] for p in client.get("/api/projects").json()] == [project["id"]]
    assert client.get(f"/api/projects/{project['id']}").json()["url"] == "https://github.com/acme/widget"


def test_invalid_url_is_rejected_without_calling_github(client, fake_github):
    response = create(client, "https://gitlab.com/acme/widget")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REPOSITORY_URL"
    assert fake_github.calls == []


def test_missing_body_field_validation_format(client):
    response = client.post("/api/projects", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"][0]["field"] == "repository_url"


def test_duplicate_project_conflict_case_insensitive(client):
    first = create(client).json()
    response = create(client, "https://github.com/ACME/Widget")
    assert response.status_code == 409 and response.json()["error"]["project_id"] == first["id"]


def test_unavailable_repository_404(client, fake_github):
    fake_github.missing = True
    response = create(client)
    assert response.status_code == 404 and response.json()["error"]["code"] == "REPOSITORY_NOT_FOUND"


def test_rate_limit_is_reported_as_429(client, fake_github):
    fake_github.rate_limited = True
    response = create(client)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "GITHUB_RATE_LIMITED" and response.json()["error"]["reset_at"]


def test_unknown_project_404(client):
    for path in ["", "/metrics", "/risk", "/history", "/recommendations", "/report"]:
        response = client.get(f"/api/projects/9999{path}")
        assert response.status_code == 404 and response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_endpoints_before_analysis_explain_what_to_do(client):
    project = create(client).json()
    response = client.get(f"/api/projects/{project['id']}/risk")
    assert response.status_code == 404 and response.json()["error"]["code"] == "NO_COMPLETED_ANALYSIS"
    history = client.get(f"/api/projects/{project['id']}/history").json()
    assert history == {"points": [], "changes": {}}


def test_full_analysis_pipeline(analyzed_project, client, fake_github):
    project, run = analyzed_project
    assert run["status"] == "PENDING"
    run = client.get(f"/api/projects/{project['id']}/runs/{run['id']}").json()
    assert run["status"] == "COMPLETED", run
    assert run["api_calls"] > 5 and fake_github.seen_auth == {"Bearer ghp_TESTTOKEN_should_never_leak_123456"}

    with SessionLocal() as db:  # data really landed in the database, normalised
        assert db.scalar(select(func.count()).select_from(Commit)) == 120
        assert db.scalar(select(func.count()).select_from(Issue)) == 40  # PR #999 filtered out
        assert db.scalar(select(func.count()).select_from(PullRequest)) == 30
        assert db.scalar(select(func.count()).select_from(Release)) == 1  # draft excluded
        unlinked = db.scalars(select(Commit.author_key).where(Commit.author_key.like("unlinked-%"))).all()
        assert unlinked and all("@" not in key for key in unlinked)  # no e-mails stored

    metrics = client.get(f"/api/projects/{project['id']}/metrics").json()["metrics"]
    by_key = {m["key"]: m for m in metrics}
    assert by_key["open_issues"]["value"] == 27
    assert by_key["contributors_90d"]["value"] >= 2
    assert by_key["median_pr_size_lines"]["value"] is not None
    assert by_key["median_pr_turnaround_days"]["definition"]

    risk = client.get(f"/api/projects/{project['id']}/risk").json()
    assert 0 <= risk["risk_score"] <= 100 and risk["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert risk["health_score"] == round(100 - risk["risk_score"], 1)
    assert abs(sum(f["contribution"] for f in risk["factors"]) - risk["risk_score"]) < 0.2
    assert risk["top_factors"] and all(f["explanation"] for f in risk["factors"])
    assert "not been empirically validated" in risk["disclaimer"]
    assert risk["ml"]["anomaly"]["status"] in {"ok", "insufficient_data"}
    assert risk["ml"]["dormancy"]["status"] in {"ok", "unreliable", "model_unavailable"}

    recs = client.get(f"/api/projects/{project['id']}/recommendations").json()
    factor_ids = {f["id"] for f in risk["factors"]}
    assert all(r["risk_factor_id"] in factor_ids for r in recs)

    listed = client.get("/api/projects").json()[0]
    assert listed["latest"]["risk_score"] == risk["risk_score"]

    activity = client.get(f"/api/projects/{project['id']}/activity").json()
    assert len(activity["weeks"]) == 52 and sum(w["commits"] for w in activity["weeks"]) > 0
    contributors = client.get(f"/api/projects/{project['id']}/contributors").json()
    assert contributors["top_authors"][0]["author"] == "alice"
    assert all("bot" not in a["author"] for a in contributors["top_authors"])


def test_cache_reuses_data_and_force_refetches(analyzed_project, client, fake_github):
    project, _ = analyzed_project
    calls = len(fake_github.calls)
    second = client.post(f"/api/projects/{project['id']}/analyze").json()
    second = client.get(f"/api/projects/{project['id']}/runs/{second['id']}").json()
    assert second["used_cache"] is True and len(fake_github.calls) == calls
    third = client.post(f"/api/projects/{project['id']}/analyze?force=true").json()
    third = client.get(f"/api/projects/{project['id']}/runs/{third['id']}").json()
    assert third["used_cache"] is False and len(fake_github.calls) > calls
    history = client.get(f"/api/projects/{project['id']}/history").json()
    assert len(history["points"]) == 3
    assert history["changes"]["7d"] is None  # no fabricated history: all runs are from today


def test_github_failure_during_analysis_marks_run_failed(client, fake_github):
    project = create(client).json()
    fake_github.fail_with = 500
    run = client.post(f"/api/projects/{project['id']}/analyze").json()
    run = client.get(f"/api/projects/{project['id']}/runs/{run['id']}").json()
    assert run["status"] == "FAILED" and run["error_code"] == "GITHUB_UNAVAILABLE"
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Commit)) == 0  # partial data rolled back


def test_rate_limit_during_analysis(client, fake_github):
    project = create(client).json()
    fake_github.rate_limited = True
    run = client.post(f"/api/projects/{project['id']}/analyze").json()
    run = client.get(f"/api/projects/{project['id']}/runs/{run['id']}").json()
    assert run["status"] == "FAILED" and run["error_code"] == "GITHUB_RATE_LIMITED"


def test_empty_repository_analysis(client, fake_github):
    fake_github.empty = True
    project = create(client).json()
    run = client.post(f"/api/projects/{project['id']}/analyze").json()
    run = client.get(f"/api/projects/{project['id']}/runs/{run['id']}").json()
    assert run["status"] == "COMPLETED"
    assert any("No commits" in n for n in run["collection_notes"])
    risk = client.get(f"/api/projects/{project['id']}/risk").json()
    assert risk["coverage"] < 1
    assert client.get(f"/api/projects/{project['id']}/report").status_code == 200


def test_simulation_endpoint(analyzed_project, client):
    project, _ = analyzed_project
    response = client.post(f"/api/projects/{project['id']}/simulate",
                           json={"overrides": {"median_pr_turnaround_days": 0.5, "top_contributor_share": 0.2}})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["label"].startswith("SIMULATION / ESTIMATE")
    assert body["simulated_score"] <= body["baseline_score"]
    assert body["difference"] == round(body["simulated_score"] - body["baseline_score"], 1)
    assert len(body["dimensions"]) == 5


def test_simulation_validation(analyzed_project, client):
    project, _ = analyzed_project
    for overrides in [{}, {"unknown_metric": 1}, {"stale_open_pr_ratio": 7}]:
        response = client.post(f"/api/projects/{project['id']}/simulate", json={"overrides": overrides})
        assert response.status_code == 422 and response.json()["error"]["code"] == "INVALID_SIMULATION"
    response = client.post(f"/api/projects/{project['id']}/simulate", json={"overrides": {"x": "abc"}})
    assert response.status_code == 422


def test_report_is_a_pdf(analyzed_project, client):
    project, _ = analyzed_project
    client.post(f"/api/projects/{project['id']}/simulate", json={"overrides": {"median_pr_turnaround_days": 1}})
    response = client.get(f"/api/projects/{project['id']}/report")
    assert response.status_code == 200 and response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF") and len(response.content) > 3000
    assert "attachment" in response.headers["content-disposition"]


def test_analysis_conflict_when_run_active(client):
    project = create(client).json()
    with SessionLocal() as db:
        from app.models import AnalysisRun
        db.add(AnalysisRun(project_id=project["id"], status="RUNNING"))
        db.commit()
    response = client.post(f"/api/projects/{project['id']}/analyze")
    assert response.status_code == 409 and response.json()["error"]["code"] == "ANALYSIS_IN_PROGRESS"


def test_delete_project_cascades(analyzed_project, client):
    project, _ = analyzed_project
    assert client.delete(f"/api/projects/{project['id']}").status_code == 204
    assert client.get(f"/api/projects/{project['id']}").status_code == 404
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(RiskFactor)) == 0
        actions = set(db.scalars(select(AuditLog.action)))
        assert {"project_created", "analysis_requested", "project_deleted"} <= actions


def test_meta_endpoints(client):
    assert "median_pr_turnaround_days" in client.get("/api/metrics/definitions").json()
    model = client.get("/api/risk-model").json()
    assert model["config"]["dimensions"]["activity"]["weight"] == 0.25
    assert "median_pr_turnaround_days" in model["simulatable_metrics"]
    assert client.get("/api/ml/model-card").json()["status"] in {"ok", "model_unavailable"}
