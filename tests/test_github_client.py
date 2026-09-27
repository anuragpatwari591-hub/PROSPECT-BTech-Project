from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app import github_client
from app.github_client import GitHubClient, InvalidRepoUrlError, build_metrics, parse_repo_url


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/octocat/Hello-World", ("octocat", "Hello-World")),
        ("http://github.com/octocat/Hello-World/", ("octocat", "Hello-World")),
        ("https://github.com/octocat/Hello-World.git", ("octocat", "Hello-World")),
        ("github.com/octocat/Hello-World", ("octocat", "Hello-World")),
        ("octocat/Hello-World", ("octocat", "Hello-World")),
    ],
)
def test_parse_repo_url_valid(url, expected):
    assert parse_repo_url(url) == expected


@pytest.mark.parametrize("bad_url", ["", "not a url", "https://example.com/foo", "justoneword"])
def test_parse_repo_url_invalid(bad_url):
    with pytest.raises(InvalidRepoUrlError):
        parse_repo_url(bad_url)


def _iso(days_ago):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


def test_build_metrics_uses_only_real_api_data():
    client = GitHubClient(token=None)

    repo_info = {
        "full_name": "acme/widget",
        "description": "A widget",
        "language": "Python",
        "stargazers_count": 42,
        "forks_count": 7,
        "archived": False,
        "pushed_at": _iso(3),
        "html_url": "https://github.com/acme/widget",
        "subscribers_count": 5,
        "default_branch": "main",
        "created_at": _iso(400),
    }
    contributors = [
        {"login": "alice", "contributions": 80},
        {"login": "bob", "contributions": 20},
    ]
    issues = [
        {"state": "open", "created_at": _iso(5)},
        {"state": "closed", "created_at": _iso(100)},
        {"state": "open", "created_at": _iso(200), "pull_request": None},  # excluded: is a PR
    ]
    pulls = [
        {"state": "open", "created_at": _iso(10)},
        {"state": "closed", "created_at": _iso(30), "merged_at": _iso(28)},
        {"state": "closed", "created_at": _iso(60), "merged_at": None},
    ]
    releases = [{"published_at": _iso(15)}]

    with patch.object(client, "get_repo", return_value=repo_info), patch.object(
        client, "get_commits", return_value=[{"author": {"login": "alice"}}]
    ), patch.object(client, "get_contributors", return_value=contributors), patch.object(
        client, "get_issues", return_value=[i for i in issues if "pull_request" not in i]
    ), patch.object(client, "get_pulls", return_value=pulls), patch.object(
        client, "get_releases", return_value=releases
    ):
        extra, metrics = build_metrics(client, "acme", "widget")

    assert extra["full_name"] == "acme/widget"
    assert extra["stars"] == 42
    assert metrics.contributor_count == 2
    assert metrics.top_contributor_pct == 80.0
    assert metrics.open_issue_count == 1
    assert metrics.closed_issue_count == 1
    assert metrics.open_pr_count == 1
    assert metrics.merged_pr_count == 1
    assert metrics.closed_unmerged_pr_count == 1
    assert metrics.release_count == 1
    assert metrics.days_since_last_release == 15
    assert metrics.archived is False


def test_get_issues_excludes_pull_requests():
    client = GitHubClient(token=None)
    raw_items = [
        {"state": "open", "created_at": _iso(1)},
        {"state": "open", "created_at": _iso(1), "pull_request": {"url": "x"}},
    ]
    with patch.object(client, "_get_all_pages", return_value=raw_items):
        issues = client.get_issues("acme", "widget")
    assert len(issues) == 1


def test_repo_not_found_raises():
    client = GitHubClient(token=None)
    with patch.object(client.session, "get", return_value=_mock_response({}, status_code=404)):
        with pytest.raises(github_client.RepoNotFoundError):
            client.get_repo("nonexistent-owner-xyz", "nonexistent-repo-xyz")


def test_get_all_pages_handles_empty_body_from_empty_repo():
    """GitHub returns a 200 with an empty body (no JSON) for endpoints like
    contributors/commits on a repository that has no commits yet. This must
    not raise a JSONDecodeError."""
    client = GitHubClient(token=None)
    empty_resp = MagicMock()
    empty_resp.status_code = 200
    empty_resp.content = b""
    empty_resp.text = ""

    with patch.object(client.session, "get", return_value=empty_resp):
        result = client._get_all_pages("/repos/acme/empty/contributors", max_pages=2)

    assert result == []


def test_build_metrics_survives_empty_repository():
    client = GitHubClient(token=None)
    repo_info = {
        "full_name": "acme/empty",
        "description": None,
        "language": None,
        "stargazers_count": 0,
        "forks_count": 0,
        "archived": False,
        "pushed_at": _iso(0),
        "html_url": "https://github.com/acme/empty",
    }
    with patch.object(client, "get_repo", return_value=repo_info), patch.object(
        client, "get_commits", return_value=[]
    ), patch.object(client, "get_contributors", return_value=[]), patch.object(
        client, "get_issues", return_value=[]
    ), patch.object(client, "get_pulls", return_value=[]), patch.object(
        client, "get_releases", return_value=[]
    ):
        extra, metrics = build_metrics(client, "acme", "empty")

    assert metrics.contributor_count == 0
    assert metrics.open_issue_count == 0
    assert metrics.release_count == 0
    assert metrics.days_since_last_release is None
