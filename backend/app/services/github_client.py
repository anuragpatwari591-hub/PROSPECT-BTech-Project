"""Thin, defensive client for the GitHub REST API.

Responsibilities: URL validation, authentication, pagination (Link header), rate-limit detection,
bounded retries for transient 5xx errors, and counting API calls. It returns raw JSON; normalisation
happens in collector.py so this file stays small and easy to mock in tests.
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

REPO_URL_RE = re.compile(
    r"^(?:https?://(?:www\.)?github\.com/)?"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$"
)


class GitHubError(Exception):
    status_code = 502
    code = "GITHUB_ERROR"

    def __init__(self, message: str, **extra):
        super().__init__(message)
        self.message = message
        self.extra = extra


class InvalidRepositoryURL(GitHubError):
    status_code = 422
    code = "INVALID_REPOSITORY_URL"


class RepositoryNotFound(GitHubError):
    status_code = 404
    code = "REPOSITORY_NOT_FOUND"


class RateLimited(GitHubError):
    status_code = 429
    code = "GITHUB_RATE_LIMITED"


class GitHubUnavailable(GitHubError):
    status_code = 503
    code = "GITHUB_UNAVAILABLE"


def parse_repo_url(url: str) -> tuple[str, str]:
    """Return (owner, repo) for 'https://github.com/owner/repo' or 'owner/repo'. Raises InvalidRepositoryURL."""
    candidate = (url or "").strip()
    if len(candidate) > 300:
        raise InvalidRepositoryURL("Repository URL is too long.")
    match = REPO_URL_RE.match(candidate)
    if not match or match.group("repo") in {".", ".."}:
        raise InvalidRepositoryURL(
            "Enter a GitHub repository URL like https://github.com/owner/repository."
        )
    return match.group("owner"), match.group("repo")


@dataclass
class PageResult:
    items: list[dict]
    truncated: bool


class GitHubClient:
    def __init__(self, token: str | None = None, base_url: str = "https://api.github.com",
                 timeout: float = 20.0, max_retries: int = 2, transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "PROSPECT-risk-analysis",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(base_url=base_url, headers=headers, timeout=timeout, transport=transport)
        self.max_retries = max_retries
        self._sleep = sleep
        self.calls = 0
        self.rate_remaining: int | None = None
        self.authenticated = bool(token)

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------------ low level
    def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        attempt = 0
        while True:
            self.calls += 1
            try:
                response = self._client.get(url, params=params)
            except httpx.TransportError as exc:
                if attempt < self.max_retries:
                    attempt += 1
                    self._sleep(2**attempt)
                    continue
                raise GitHubUnavailable("Could not reach GitHub. Check your network and try again.") from exc

            remaining = response.headers.get("x-ratelimit-remaining")
            if remaining is not None and remaining.isdigit():
                self.rate_remaining = int(remaining)

            if response.status_code in (403, 429) and (
                remaining == "0" or "rate limit" in response.text.lower() or response.status_code == 429
            ):
                reset = response.headers.get("x-ratelimit-reset")
                reset_at = datetime.fromtimestamp(int(reset), UTC).isoformat() if reset and reset.isdigit() else None
                hint = "" if self.authenticated else " Configure GITHUB_TOKEN on the server to raise the limit."
                raise RateLimited(f"GitHub API rate limit reached.{hint}", reset_at=reset_at)
            if response.status_code == 404:
                raise RepositoryNotFound("Repository not found, or it is private.")
            if response.status_code == 401:
                raise GitHubError("GitHub rejected the configured token (401). Check GITHUB_TOKEN.")
            if response.status_code >= 500:
                if attempt < self.max_retries:
                    attempt += 1
                    self._sleep(2**attempt)
                    continue
                raise GitHubUnavailable(f"GitHub returned {response.status_code}. Try again later.")
            return response

    def paginate(self, path: str, params: dict | None = None, max_pages: int = 5,
                 stop: Callable[[dict], bool] | None = None) -> PageResult:
        """Follow Link: rel="next" up to max_pages. `stop(item)` ends collection early (e.g. older than window)."""
        items: list[dict] = []
        url: str | None = path
        query = {"per_page": 100, **(params or {})}
        pages = 0
        while url and pages < max_pages:
            response = self._get(url, params=query if pages == 0 else None)
            if response.status_code == 409:  # empty repository (e.g. commits endpoint)
                return PageResult(items=[], truncated=False)
            if response.status_code >= 400:
                raise GitHubError(f"GitHub returned {response.status_code} for {path}.")
            pages += 1
            for item in response.json():
                if stop and stop(item):
                    return PageResult(items=items, truncated=False)
                items.append(item)
            url = response.links.get("next", {}).get("url")
        return PageResult(items=items, truncated=bool(url))

    # ------------------------------------------------------------------ endpoints
    def get_repository(self, owner: str, repo: str) -> dict:
        response = self._get(f"/repos/{owner}/{repo}")
        if response.status_code >= 400:
            raise GitHubError(f"GitHub returned {response.status_code}.")
        return response.json()

    def list_commits(self, owner: str, repo: str, since: datetime, max_pages: int) -> PageResult:
        return self.paginate(f"/repos/{owner}/{repo}/commits", {"since": since.isoformat()}, max_pages)

    def list_issues(self, owner: str, repo: str, state: str, max_pages: int,
                    since: datetime | None = None) -> PageResult:
        params = {"state": state, "sort": "updated", "direction": "desc"}
        if since:
            params["since"] = since.isoformat()
        return self.paginate(f"/repos/{owner}/{repo}/issues", params, max_pages)

    def list_pulls(self, owner: str, repo: str, state: str, max_pages: int,
                   updated_after: datetime | None = None) -> PageResult:
        params = {"state": state, "sort": "updated", "direction": "desc"}

        def older(item: dict) -> bool:
            return bool(updated_after and item.get("updated_at")
                        and datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")) < updated_after)

        return self.paginate(f"/repos/{owner}/{repo}/pulls", params, max_pages, stop=older)

    def get_pull(self, owner: str, repo: str, number: int) -> dict:
        return self._get(f"/repos/{owner}/{repo}/pulls/{number}").json()

    def list_contributors(self, owner: str, repo: str) -> PageResult:
        return self.paginate(f"/repos/{owner}/{repo}/contributors", {"anon": "false"}, max_pages=1)

    def list_releases(self, owner: str, repo: str) -> PageResult:
        return self.paginate(f"/repos/{owner}/{repo}/releases", None, max_pages=1)
