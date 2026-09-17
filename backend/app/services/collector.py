"""Collect repository data from GitHub, normalise it, and upsert it into the database.

Normalisation rules (also in docs/05_METRICS.md):
- Pull requests returned by the issues endpoint are removed (GitHub treats PRs as issues).
- Bot accounts (login ending in "[bot]" or type == "Bot") are flagged and excluded from contributor metrics.
- Commit authors without a GitHub account are stored as "unlinked-<8 hex>" — a salted hash of the e-mail —
  so concentration can be measured without storing personal data.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.time import parse_github_time, utcnow
from app.models import Commit, Contributor, Issue, Project, PullRequest, Release
from app.services.github_client import GitHubClient


@dataclass
class CollectionReport:
    api_calls: int = 0
    truncated: bool = False
    notes: list[str] = field(default_factory=list)


def is_bot_login(login: str | None, user_type: str | None = None) -> bool:
    return bool(login) and (login.lower().endswith("[bot]") or user_type == "Bot")


def author_key_for(commit: dict, salt: str) -> tuple[str, bool]:
    user = commit.get("author") or {}
    login = user.get("login")
    if login:
        return login[:80], is_bot_login(login, user.get("type"))
    email = ((commit.get("commit") or {}).get("author") or {}).get("email") or "unknown"
    digest = hashlib.sha256(f"{salt}:{email.lower()}".encode()).hexdigest()[:8]
    return f"unlinked-{digest}", "[bot]" in email or "noreply@github.com" == email.lower()


def normalize_commit(raw: dict, salt: str) -> dict | None:
    authored = parse_github_time(((raw.get("commit") or {}).get("author") or {}).get("date"))
    if not raw.get("sha") or authored is None:
        return None
    key, bot = author_key_for(raw, salt)
    return {"sha": raw["sha"], "author_key": key, "is_bot": bot, "authored_at": authored}


def normalize_issue(raw: dict) -> dict | None:
    if "pull_request" in raw:
        return None
    return {
        "number": raw["number"], "state": raw["state"], "created_at": parse_github_time(raw["created_at"]),
        "closed_at": parse_github_time(raw.get("closed_at")), "updated_at": parse_github_time(raw.get("updated_at")),
        "comments": raw.get("comments") or 0,
    }


def normalize_pull(raw: dict) -> dict:
    return {
        "number": raw["number"], "state": raw["state"], "draft": bool(raw.get("draft")),
        "created_at": parse_github_time(raw["created_at"]), "updated_at": parse_github_time(raw.get("updated_at")),
        "closed_at": parse_github_time(raw.get("closed_at")), "merged_at": parse_github_time(raw.get("merged_at")),
    }


def _upsert(db: Session, model, project_id: int, key_field: str, rows: list[dict]) -> None:
    if not rows:
        return
    keys = [r[key_field] for r in rows]
    existing = {
        getattr(obj, key_field): obj
        for obj in db.scalars(select(model).where(model.project_id == project_id,
                                                  getattr(model, key_field).in_(keys)))
    }
    for row in rows:
        obj = existing.get(row[key_field])
        if obj is None:
            db.add(model(project_id=project_id, **row))
        else:
            for name, value in row.items():
                setattr(obj, name, value)


def collect(db: Session, project: Project, client: GitHubClient, settings: Settings) -> CollectionReport:
    report = CollectionReport()
    owner, repo = project.owner, project.repo
    now = utcnow()
    since = now - timedelta(days=settings.analysis_window_days)
    pages = settings.max_pages_per_endpoint
    salt = settings.author_hash_salt.get_secret_value()

    meta = client.get_repository(owner, repo)
    project.name = meta.get("full_name") or f"{owner}/{repo}"
    project.description = (meta.get("description") or "")[:2000] or None
    project.default_branch = meta.get("default_branch")
    project.stars = meta.get("stargazers_count")
    project.forks = meta.get("forks_count")
    project.is_archived = bool(meta.get("archived"))
    project.github_created_at = parse_github_time(meta.get("created_at"))

    commits = client.list_commits(owner, repo, since, pages)
    commit_rows = {c["sha"]: c for c in filter(None, (normalize_commit(r, salt) for r in commits.items))}
    _upsert(db, Commit, project.id, "sha", list(commit_rows.values()))
    if commits.truncated:
        report.notes.append(f"Commits truncated at {len(commits.items)} (page cap); counts are lower bounds.")

    open_issues = client.list_issues(owner, repo, "open", pages)
    closed_issues = client.list_issues(owner, repo, "closed", pages, since=since)
    issue_rows = {i["number"]: i for i in filter(None, map(normalize_issue, open_issues.items + closed_issues.items))}
    _upsert(db, Issue, project.id, "number", list(issue_rows.values()))
    if open_issues.truncated or closed_issues.truncated:
        report.notes.append("Issue lists truncated (page cap); backlog metrics may be underestimated.")

    open_pulls = client.list_pulls(owner, repo, "open", pages)
    closed_pulls = client.list_pulls(owner, repo, "closed", pages, updated_after=since)
    pull_rows = {p["number"]: p for p in map(normalize_pull, open_pulls.items + closed_pulls.items)}
    # PR size needs one extra call per PR, so only a recent sample of merged PRs is enriched.
    merged = sorted((p for p in pull_rows.values() if p["merged_at"]), key=lambda p: p["merged_at"], reverse=True)
    for pr in merged[: settings.pr_detail_sample]:
        detail = client.get_pull(owner, repo, pr["number"])
        pr.update(additions=detail.get("additions"), deletions=detail.get("deletions"),
                  changed_files=detail.get("changed_files"))
    _upsert(db, PullRequest, project.id, "number", list(pull_rows.values()))
    if open_pulls.truncated or closed_pulls.truncated:
        report.notes.append("Pull request lists truncated (page cap).")

    contributors = client.list_contributors(owner, repo)
    contributor_rows = [
        {"login": c["login"][:80], "contributions": c.get("contributions", 0),
         "is_bot": is_bot_login(c["login"], c.get("type"))}
        for c in contributors.items if c.get("login")
    ]
    _upsert(db, Contributor, project.id, "login", contributor_rows)

    releases = client.list_releases(owner, repo)
    release_rows = [
        {"github_id": r["id"], "tag_name": (r.get("tag_name") or "")[:255], "prerelease": bool(r.get("prerelease")),
         "published_at": parse_github_time(r.get("published_at"))}
        for r in releases.items if not r.get("draft")
    ]
    _upsert(db, Release, project.id, "github_id", release_rows)

    project.last_collected_at = now
    report.api_calls = client.calls
    report.truncated = bool(report.notes)
    if not client.authenticated:
        report.notes.append("Collected without a GitHub token (60 requests/hour limit).")
    db.flush()
    return report
