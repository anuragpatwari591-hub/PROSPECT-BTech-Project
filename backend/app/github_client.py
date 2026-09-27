"""
Thin client around the real GitHub REST API. No data is ever fabricated:
every field returned here is read directly from GitHub's response JSON, and
if GitHub has nothing to say (e.g. no releases) we represent that as an
empty list / zero, never as an invented value.
"""
import re
from datetime import datetime, timezone
from typing import Optional

import requests

from . import config


class GitHubError(Exception):
    """Base class for GitHub client errors."""


class RepoNotFoundError(GitHubError):
    pass


class RateLimitError(GitHubError):
    pass


class InvalidRepoUrlError(GitHubError):
    pass


_URL_PATTERNS = [
    re.compile(r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(\.git)?/?$"),
    re.compile(r"^github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(\.git)?/?$"),
    re.compile(r"^(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(\.git)?$"),
]


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL or 'owner/repo' shorthand."""
    candidate = repo_url.strip()
    for pattern in _URL_PATTERNS:
        match = pattern.match(candidate)
        if match:
            owner, repo = match.group("owner"), match.group("repo")
            if owner and repo:
                return owner, repo
    raise InvalidRepoUrlError(
        f"'{repo_url}' does not look like a GitHub repository URL "
        f"(expected e.g. https://github.com/owner/repo)."
    )


def _days_since(iso_timestamp: Optional[str]) -> Optional[int]:
    if not iso_timestamp:
        return None
    dt = datetime.strptime(iso_timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    return max(delta.days, 0)


class GitHubClient:
    def __init__(self, token: Optional[str] = None, session: Optional[requests.Session] = None):
        self.token = token if token is not None else config.GITHUB_TOKEN
        self.session = session or requests.Session()
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers.update(headers)

    def _get(self, path: str, params: Optional[dict] = None) -> requests.Response:
        url = f"{config.GITHUB_API_BASE}{path}"
        resp = self.session.get(url, params=params, timeout=15)
        if resp.status_code == 404:
            raise RepoNotFoundError(f"GitHub returned 404 for {url}")
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            raise RateLimitError(
                "GitHub API rate limit exceeded. Set a GITHUB_TOKEN environment "
                "variable to raise the limit."
            )
        if resp.status_code >= 400:
            raise GitHubError(f"GitHub API error {resp.status_code} for {url}: {resp.text[:200]}")
        return resp

    def _get_all_pages(self, path: str, max_pages: int, params: Optional[dict] = None) -> list:
        items = []
        params = dict(params or {})
        params["per_page"] = 100
        for page in range(1, max_pages + 1):
            params["page"] = page
            resp = self._get(path, params=params)
            # GitHub returns 204/empty-body for e.g. contributors or commits
            # on a repository with no commits yet.
            if not resp.content:
                break
            batch = resp.json()
            if not batch:
                break
            items.extend(batch)
            if len(batch) < 100:
                break
        return items

    def get_repo(self, owner: str, repo: str) -> dict:
        return self._get(f"/repos/{owner}/{repo}").json()

    def get_commits(self, owner: str, repo: str) -> list:
        try:
            return self._get_all_pages(
                f"/repos/{owner}/{repo}/commits", config.MAX_PAGES_COMMITS
            )
        except GitHubError:
            # Empty repositories return 409 Conflict with no commits.
            return []

    def get_contributors(self, owner: str, repo: str) -> list:
        try:
            return self._get_all_pages(
                f"/repos/{owner}/{repo}/contributors",
                config.MAX_PAGES_CONTRIBUTORS,
                params={"anon": "0"},
            )
        except GitHubError:
            return []

    def get_issues(self, owner: str, repo: str) -> list:
        """Issues only (pull requests are excluded, matching GitHub's own
        distinction even though the /issues endpoint mixes both in)."""
        raw = self._get_all_pages(
            f"/repos/{owner}/{repo}/issues",
            config.MAX_PAGES_ISSUES,
            params={"state": "all"},
        )
        return [item for item in raw if "pull_request" not in item]

    def get_pulls(self, owner: str, repo: str) -> list:
        return self._get_all_pages(
            f"/repos/{owner}/{repo}/pulls",
            config.MAX_PAGES_PULLS,
            params={"state": "all"},
        )

    def get_releases(self, owner: str, repo: str) -> list:
        return self._get_all_pages(
            f"/repos/{owner}/{repo}/releases", config.MAX_PAGES_RELEASES
        )


def build_metrics(client: GitHubClient, owner: str, repo: str):
    """Fetch everything needed from the real GitHub API and return
    (repo_info, RepoMetrics). Kept separate from risk_engine so the engine
    itself never touches the network."""
    from .risk_engine import RepoMetrics  # local import avoids a cycle

    repo_info = client.get_repo(owner, repo)
    commits = client.get_commits(owner, repo)
    contributors = client.get_contributors(owner, repo)
    issues = client.get_issues(owner, repo)
    pulls = client.get_pulls(owner, repo)
    releases = client.get_releases(owner, repo)

    days_since_last_push = _days_since(repo_info.get("pushed_at"))

    contributor_count = len(contributors)
    top_contributor_pct = 0.0
    if contributors:
        total_contribs = sum(c.get("contributions", 0) for c in contributors)
        if total_contribs > 0:
            top_contributor_pct = round(
                (contributors[0].get("contributions", 0) / total_contribs) * 100, 1
            )
    elif commits:
        # Fallback for repos where the contributors endpoint is empty/pending
        # (GitHub computes contributor stats asynchronously): derive the same
        # signal from the sampled commit authors instead.
        author_counts: dict[str, int] = {}
        for c in commits:
            author = (c.get("author") or {}).get("login") or (
                (c.get("commit") or {}).get("author") or {}
            ).get("name") or "unknown"
            author_counts[author] = author_counts.get(author, 0) + 1
        contributor_count = len(author_counts)
        if author_counts:
            top = max(author_counts.values())
            top_contributor_pct = round((top / len(commits)) * 100, 1)

    open_issues = [i for i in issues if i.get("state") == "open"]
    closed_issues = [i for i in issues if i.get("state") == "closed"]
    stale_open_issues = [
        i for i in open_issues
        if (_days_since(i.get("created_at")) or 0) > config.STALE_ISSUE_DAYS
    ]

    open_pulls = [p for p in pulls if p.get("state") == "open"]
    closed_pulls = [p for p in pulls if p.get("state") == "closed"]
    merged_pulls = [p for p in closed_pulls if p.get("merged_at")]
    closed_unmerged_pulls = [p for p in closed_pulls if not p.get("merged_at")]
    stale_open_pulls = [
        p for p in open_pulls
        if (_days_since(p.get("created_at")) or 0) > config.STALE_PR_DAYS
    ]

    release_count = len(releases)
    days_since_last_release = _days_since(releases[0]["published_at"]) if releases else None

    metrics = RepoMetrics(
        archived=bool(repo_info.get("archived", False)),
        days_since_last_push=days_since_last_push,
        contributor_count=contributor_count,
        top_contributor_pct=top_contributor_pct,
        open_issue_count=len(open_issues),
        closed_issue_count=len(closed_issues),
        stale_open_issue_count=len(stale_open_issues),
        open_pr_count=len(open_pulls),
        closed_unmerged_pr_count=len(closed_unmerged_pulls),
        merged_pr_count=len(merged_pulls),
        stale_open_pr_count=len(stale_open_pulls),
        release_count=release_count,
        days_since_last_release=days_since_last_release,
    )

    extra = {
        "full_name": repo_info.get("full_name"),
        "description": repo_info.get("description"),
        "language": repo_info.get("language"),
        "stars": repo_info.get("stargazers_count", 0),
        "forks": repo_info.get("forks_count", 0),
        "watchers": repo_info.get("subscribers_count", 0),
        "default_branch": repo_info.get("default_branch"),
        "created_at": repo_info.get("created_at"),
        "pushed_at": repo_info.get("pushed_at"),
        "html_url": repo_info.get("html_url"),
        "sampled_commits": len(commits),
        "sampled_issues": len(issues),
        "sampled_pulls": len(pulls),
    }

    return extra, metrics
