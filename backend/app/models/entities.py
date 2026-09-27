"""Database schema for PROSPECT.

Design notes
- Project merges the "Project" and "Repository" concepts: one project tracks one GitHub repository (MVP).
- Raw GitHub entities (Commit, Issue, PullRequest, Release, Contributor) are stored once per project and
  upserted on each analysis, so repeated analyses do not duplicate data.
- Everything computed (metrics, risk, factors, recommendations) hangs off an AnalysisRun, so the history of
  every run is preserved exactly as it was calculated.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import utcnow

RUN_STATUSES = ("PENDING", "RUNNING", "COMPLETED", "FAILED")
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("owner", "repo", name="uq_project_owner_repo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    owner: Mapped[str] = mapped_column(String(39))
    repo: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    default_branch: Mapped[str | None] = mapped_column(String(255))
    stars: Mapped[int | None] = mapped_column(Integer)
    forks: Mapped[int | None] = mapped_column(Integer)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    github_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Commit(Base):
    __tablename__ = "commits"
    __table_args__ = (
        UniqueConstraint("project_id", "sha", name="uq_commit_project_sha"),
        Index("ix_commits_project_time", "project_id", "authored_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    sha: Mapped[str] = mapped_column(String(40))
    # GitHub login, or "unlinked-<hash>" when the commit e-mail is not linked to an account.
    author_key: Mapped[str] = mapped_column(String(80))
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    authored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_issue_project_number"),
        CheckConstraint("state IN ('open','closed')", name="ck_issue_state"),
        Index("ix_issues_project_state", "project_id", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comments: Mapped[int] = mapped_column(Integer, default=0)


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_pr_project_number"),
        CheckConstraint("state IN ('open','closed')", name="ck_pr_state"),
        Index("ix_prs_project_state", "project_id", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(10))
    draft: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    additions: Mapped[int | None] = mapped_column(Integer)
    deletions: Mapped[int | None] = mapped_column(Integer)
    changed_files: Mapped[int | None] = mapped_column(Integer)


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (UniqueConstraint("project_id", "github_id", name="uq_release_project_ghid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    github_id: Mapped[int] = mapped_column(Integer)
    tag_name: Mapped[str] = mapped_column(String(255))
    prerelease: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Contributor(Base):
    """All-time contribution counts as reported by GitHub's contributors endpoint."""

    __tablename__ = "contributors"
    __table_args__ = (UniqueConstraint("project_id", "login", name="uq_contributor_project_login"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    login: Mapped[str] = mapped_column(String(80))
    contributions: Mapped[int] = mapped_column(Integer, default=0)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        CheckConstraint(f"status IN {RUN_STATUSES}", name="ck_run_status"),
        Index("ix_runs_project_started", "project_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(12), default="PENDING")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(40))
    error_message: Mapped[str | None] = mapped_column(Text)
    used_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    api_calls: Mapped[int] = mapped_column(Integer, default=0)
    data_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    collection_notes: Mapped[list | None] = mapped_column(JSON)
    ml_output: Mapped[dict | None] = mapped_column(JSON)

    project: Mapped[Project] = relationship(back_populates="runs")
    metrics: Mapped[list["RepositoryMetric"]] = relationship(cascade="all, delete-orphan")
    assessment: Mapped["RiskAssessment | None"] = relationship(cascade="all, delete-orphan", uselist=False)


class RepositoryMetric(Base):
    __tablename__ = "repository_metrics"
    __table_args__ = (UniqueConstraint("run_id", "key", name="uq_metric_run_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(60))
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(Text)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="ck_risk_range"),
        CheckConstraint(f"risk_level IN {RISK_LEVELS}", name="ck_risk_level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"), unique=True)
    risk_score: Mapped[float] = mapped_column(Float)
    health_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(10))
    coverage: Mapped[float] = mapped_column(Float)
    config_snapshot: Mapped[dict] = mapped_column(JSON)
    dimensions: Mapped[list] = mapped_column(JSON)
    engine_version: Mapped[str] = mapped_column(String(20))

    factors: Mapped[list["RiskFactor"]] = relationship(cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(cascade="all, delete-orphan")


class RiskFactor(Base):
    __tablename__ = "risk_factors"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("risk_assessments.id", ondelete="CASCADE"), index=True)
    dimension: Mapped[str] = mapped_column(String(30))
    signal_key: Mapped[str] = mapped_column(String(60))
    metric_key: Mapped[str] = mapped_column(String(60))
    metric_value: Mapped[float | None] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    contribution: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(10))
    explanation: Mapped[str] = mapped_column(Text)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("risk_assessments.id", ondelete="CASCADE"), index=True)
    risk_factor_id: Mapped[int | None] = mapped_column(ForeignKey("risk_factors.id", ondelete="SET NULL"))
    signal_key: Mapped[str] = mapped_column(String(60))
    priority: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text)


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    overrides: Mapped[dict] = mapped_column(JSON)
    baseline_score: Mapped[float] = mapped_column(Float)
    simulated_score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    """Security-relevant actions. Stores no IP addresses or personal data."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
