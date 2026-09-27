from unittest.mock import patch

from app import github_client
from app.risk_engine import RepoMetrics


def _fake_extra(name="acme/widget"):
    return {
        "full_name": name,
        "description": "demo",
        "language": "Python",
        "stars": 10,
        "forks": 2,
        "html_url": f"https://github.com/{name}",
        "created_at": "2020-01-01T00:00:00Z",
        "pushed_at": "2024-01-01T00:00:00Z",
    }


def _fake_metrics(**overrides):
    base = dict(
        archived=False,
        days_since_last_push=2,
        contributor_count=10,
        top_contributor_pct=20.0,
        open_issue_count=3,
        closed_issue_count=30,
        stale_open_issue_count=0,
        open_pr_count=1,
        closed_unmerged_pr_count=2,
        merged_pr_count=30,
        stale_open_pr_count=0,
        release_count=5,
        days_since_last_release=20,
    )
    base.update(overrides)
    return RepoMetrics(**base)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_analyze_invalid_url(client):
    resp = client.post("/api/analyze", json={"repo_url": "not a url"})
    assert resp.status_code == 422


def test_analyze_repo_not_found(client):
    with patch.object(
        github_client, "build_metrics", side_effect=github_client.RepoNotFoundError("x")
    ):
        resp = client.post(
            "/api/analyze", json={"repo_url": "https://github.com/nobody/nothing"}
        )
    assert resp.status_code == 404


def test_analyze_success_and_history_roundtrip(client):
    with patch.object(
        github_client, "build_metrics", return_value=(_fake_extra(), _fake_metrics())
    ):
        resp = client.post(
            "/api/analyze", json={"repo_url": "https://github.com/acme/widget"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["repo_full_name"] == "acme/widget"
    assert 0 <= data["risk_score"] <= 100
    assert data["classification"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert len(data["factors"]) == 5
    analysis_id = data["id"]

    hist_resp = client.get("/api/history")
    assert hist_resp.status_code == 200
    assert any(item["id"] == analysis_id for item in hist_resp.json())

    detail_resp = client.get(f"/api/history/{analysis_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["repo_full_name"] == "acme/widget"


def test_history_item_not_found(client):
    resp = client.get("/api/history/999999")
    assert resp.status_code == 404


def test_what_if_simulation(client):
    with patch.object(
        github_client, "build_metrics", return_value=(_fake_extra(), _fake_metrics())
    ):
        analyze_resp = client.post(
            "/api/analyze", json={"repo_url": "https://github.com/acme/widget"}
        )
    analysis_id = analyze_resp.json()["id"]
    base_score = analyze_resp.json()["risk_score"]

    whatif_resp = client.post(
        f"/api/whatif/{analysis_id}",
        json={"overrides": {"contributor_count": 1, "top_contributor_pct": 100.0}},
    )
    assert whatif_resp.status_code == 200
    sim = whatif_resp.json()
    assert sim["is_simulation"] is True
    assert sim["risk_score"] >= base_score

    # The original stored analysis must be unchanged by the simulation.
    original_resp = client.get(f"/api/history/{analysis_id}")
    assert original_resp.json()["risk_score"] == base_score


def test_what_if_rejects_unknown_field(client):
    with patch.object(
        github_client, "build_metrics", return_value=(_fake_extra(), _fake_metrics())
    ):
        analyze_resp = client.post(
            "/api/analyze", json={"repo_url": "https://github.com/acme/widget"}
        )
    analysis_id = analyze_resp.json()["id"]
    resp = client.post(
        f"/api/whatif/{analysis_id}", json={"overrides": {"not_a_real_field": 1}}
    )
    assert resp.status_code == 422


def test_report_pdf_download(client):
    with patch.object(
        github_client, "build_metrics", return_value=(_fake_extra(), _fake_metrics())
    ):
        analyze_resp = client.post(
            "/api/analyze", json={"repo_url": "https://github.com/acme/widget"}
        )
    analysis_id = analyze_resp.json()["id"]

    resp = client.get(f"/api/report/{analysis_id}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_report_not_found(client):
    resp = client.get("/api/report/999999")
    assert resp.status_code == 404
