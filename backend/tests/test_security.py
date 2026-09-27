"""Security tests: secret exposure, headers, CORS, injection-style input, error hygiene."""

import subprocess
from pathlib import Path

from app.core.config import Settings
from tests.conftest import TEST_TOKEN

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_token_never_appears_in_any_response(analyzed_project, client):
    project, run = analyzed_project
    pid = project["id"]
    paths = ["/api/health", "/api/projects", f"/api/projects/{pid}", f"/api/projects/{pid}/risk",
             f"/api/projects/{pid}/metrics", f"/api/projects/{pid}/runs", "/api/risk-model", "/openapi.json",
             f"/api/projects/{pid}/report"]
    for path in paths:
        response = client.get(path)
        assert TEST_TOKEN.encode() not in response.content, path
        assert TEST_TOKEN not in str(response.headers), path


def test_settings_repr_hides_token():
    settings = Settings(github_token="ghp_secret_value_xyz")
    assert "ghp_secret_value_xyz" not in repr(settings) and "ghp_secret_value_xyz" not in str(settings.model_dump())


def test_security_headers(client):
    headers = client.get("/api/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in headers["content-security-policy"]


def test_cors_allows_only_configured_origins(client):
    ok = client.options("/api/projects", headers={"Origin": "http://localhost:5173",
                                                  "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.get("/api/projects", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_sql_injection_style_input_is_rejected_and_harmless(client):
    payloads = ["https://github.com/a/b' OR '1'='1", "https://github.com/a/b;DROP TABLE projects",
                "a/b\x00", "<script>alert(1)</script>/x"]
    for payload in payloads:
        response = client.post("/api/projects", json={"repository_url": payload})
        assert response.status_code == 422
    assert client.get("/api/projects").status_code == 200  # table still exists


def test_path_parameter_type_validation(client):
    assert client.get("/api/projects/1%20OR%201=1").status_code == 422


def test_unhandled_errors_do_not_leak_stack_traces(client, monkeypatch):
    from app.api.routes import projects

    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    from app.core.database import SessionLocal
    from app.models import Project
    with SessionLocal() as db:
        db.add(Project(name="a/b", owner="a", repo="b", url="https://github.com/a/b"))
        db.commit()
    monkeypatch.setattr(projects, "_project_out", boom)
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as raw:
        response = raw.get("/api/projects")
    assert response.status_code == 500
    assert "secret internal detail" not in response.text and "Traceback" not in response.text


def test_no_secret_files_tracked_by_git():
    result = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True)  # noqa: S603,S607
    if result.returncode != 0:
        return
    tracked = result.stdout.splitlines()
    assert not any(Path(f).name == ".env" for f in tracked)


def test_no_hardcoded_github_tokens_in_source():
    patterns = ("ghp_", "github_pat_", "gho_")
    sources = [*(REPO_ROOT / "backend" / "app").rglob("*.py"), *(REPO_ROOT / "frontend" / "src").rglob("*.ts*")]
    for path in sources:
        text = path.read_text(errors="ignore")
        assert not any(p in text for p in patterns), path


def test_platform_database_urls_are_normalised():
    assert Settings(database_url="postgres://u:p@h:5432/d").database_url == "postgresql+psycopg://u:p@h:5432/d"
    assert Settings(database_url="postgresql://u:p@h/d").database_url == "postgresql+psycopg://u:p@h/d"
    assert Settings(database_url="sqlite:///x.db").database_url == "sqlite:///x.db"
