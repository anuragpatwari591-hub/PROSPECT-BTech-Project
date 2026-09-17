"""A small in-memory fake of the GitHub REST API served through httpx.MockTransport.

It produces realistic payload shapes (including Link-header pagination) so that tests exercise the real
GitHubClient, collector, engines and API end-to-end without network access.
"""

import json
import re
from datetime import UTC, datetime, timedelta

import httpx


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeGitHub:
    def __init__(self, owner="acme", repo="widget", now: datetime | None = None):
        self.owner, self.repo = owner, repo
        self.now = now or datetime.now(UTC)
        self.calls: list[str] = []
        self.fail_with: int | None = None
        self.rate_limited = False
        self.empty = False
        self.missing = False
        self.seen_auth: set[str] = set()
        self._build()

    def _build(self):
        n = self.now
        # 120 commits over ~200 days: alice dominates, bots excluded, one unlinked author
        self.commits = []
        for i in range(120):
            login = "alice" if i % 4 else "bob"
            author = {"login": login, "type": "User"}
            if i % 15 == 0:
                author = None
            if i % 20 == 1:
                author = {"login": "dependabot[bot]", "type": "Bot"}
            days_ago = i * 1.7 + 0.5
            self.commits.append({"sha": f"{i:040x}", "author": author,
                                 "commit": {"author": {"date": iso(n - timedelta(days=days_ago)),
                                                       "email": f"dev{i % 3}@example.com"}}})
        self.issues = []
        for i in range(1, 41):
            created = n - timedelta(days=5 + i * 4)
            closed = created + timedelta(days=3) if i % 3 == 0 else None
            self.issues.append({"number": i, "state": "closed" if closed else "open", "created_at": iso(created),
                                "updated_at": iso(closed or created), "closed_at": iso(closed) if closed else None,
                                "comments": i % 5})
        self.issues.append({"number": 999, "state": "open", "created_at": iso(n - timedelta(days=2)),
                            "updated_at": iso(n), "closed_at": None, "pull_request": {"url": "x"}})
        self.pulls = []
        for i in range(1, 31):
            created = n - timedelta(days=2 + i * 3)
            merged = created + timedelta(days=1 + i % 6) if i % 5 else None
            state = "closed" if merged or i % 10 == 0 else "open"
            self.pulls.append({"number": 1000 + i, "state": state, "draft": False, "created_at": iso(created),
                               "updated_at": iso(merged or created), "closed_at": iso(merged) if merged else None,
                               "merged_at": iso(merged) if merged else None})
        self.releases = [{"id": 1, "tag_name": "v1.0", "draft": False, "prerelease": False,
                          "published_at": iso(n - timedelta(days=120))},
                         {"id": 2, "tag_name": "v1.1-draft", "draft": True, "prerelease": False,
                          "published_at": None}]
        self.contributors = [{"login": "alice", "contributions": 300, "type": "User"},
                             {"login": "bob", "contributions": 80, "type": "User"},
                             {"login": "dependabot[bot]", "contributions": 40, "type": "Bot"}]

    # ------------------------------------------------------------------ routing
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def _page(self, request: httpx.Request, items: list) -> httpx.Response:
        per_page = int(request.url.params.get("per_page", 30))
        page = int(request.url.params.get("page", 1))
        chunk = items[(page - 1) * per_page: page * per_page]
        headers = {"x-ratelimit-remaining": "4999"}
        if page * per_page < len(items):
            params = dict(request.url.params)
            params["page"] = str(page + 1)
            headers["link"] = f'<{request.url.copy_with(params=params)}>; rel="next"'
        return httpx.Response(200, headers=headers, content=json.dumps(chunk))

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append(path)
        if "authorization" in request.headers:
            self.seen_auth.add(request.headers["authorization"])
        if self.rate_limited:
            return httpx.Response(403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1900000000"},
                                  json={"message": "API rate limit exceeded"})
        if self.fail_with:
            return httpx.Response(self.fail_with, json={"message": "boom"})
        base = f"/repos/{self.owner}/{self.repo}"
        if self.missing or not path.startswith(base):
            return httpx.Response(404, json={"message": "Not Found"})
        rest = path[len(base):]
        if rest == "":
            return httpx.Response(200, json={"full_name": f"{self.owner}/{self.repo}", "description": "A widget",
                                             "default_branch": "main", "stargazers_count": 42, "forks_count": 7,
                                             "archived": False, "created_at": iso(self.now - timedelta(days=900))})
        if rest == "/commits":
            if self.empty:
                return httpx.Response(409, json={"message": "Git Repository is empty."})
            return self._page(request, self.commits)
        if rest == "/issues":
            if self.empty:
                return self._page(request, [])
            state = request.url.params.get("state")
            return self._page(request, [i for i in self.issues if i["state"] == state])
        if rest == "/pulls":
            if self.empty:
                return self._page(request, [])
            state = request.url.params.get("state")
            items = sorted((p for p in self.pulls if p["state"] == state), key=lambda p: p["updated_at"], reverse=True)
            return self._page(request, items)
        if m := re.fullmatch(r"/pulls/(\d+)", rest):
            number = int(m.group(1))
            return httpx.Response(200, json={"number": number, "additions": number % 400 + 50,
                                             "deletions": number % 90, "changed_files": 3})
        if rest == "/contributors":
            return self._page(request, [] if self.empty else self.contributors)
        if rest == "/releases":
            return self._page(request, [] if self.empty else self.releases)
        return httpx.Response(404, json={"message": "Not Found"})
