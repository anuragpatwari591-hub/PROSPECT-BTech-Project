import os
import tempfile
from pathlib import Path

# Configure the app BEFORE it is imported. PostgreSQL is used when TEST_DATABASE_URL is set (CI does this).
_tmp = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}")
os.environ["ENVIRONMENT"] = "test"
os.environ["GITHUB_TOKEN"] = "ghp_TESTTOKEN_should_never_leak_123456"
os.environ["CACHE_TTL_MINUTES"] = "30"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.deps import get_client_factory  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.github_client import GitHubClient  # noqa: E402
from tests.fake_github import FakeGitHub  # noqa: E402

TEST_TOKEN = os.environ["GITHUB_TOKEN"]


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def fake_github():
    return FakeGitHub()


@pytest.fixture
def client(fake_github):
    def factory():
        return GitHubClient(token=TEST_TOKEN, transport=fake_github.transport(), sleep=lambda _: None)

    app.dependency_overrides[get_client_factory] = lambda: factory
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def analyzed_project(client):
    """A project with one completed analysis (TestClient runs background tasks before returning)."""
    project = client.post("/api/projects", json={"repository_url": "https://github.com/acme/widget"}).json()
    run = client.post(f"/api/projects/{project['id']}/analyze").json()
    return project, run
