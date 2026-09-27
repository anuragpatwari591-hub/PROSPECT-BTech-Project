from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from .database import Base


class Analysis(Base):
    """One stored run of the risk engine against a real GitHub repository."""

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    repo_full_name = Column(String, index=True, nullable=False)
    repo_url = Column(String, nullable=False)
    description = Column(String, nullable=True)
    primary_language = Column(String, nullable=True)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)

    risk_score = Column(Float, nullable=False)
    health_score = Column(Float, nullable=False)
    classification = Column(String, nullable=False)

    metrics_json = Column(Text, nullable=False)
    factors_json = Column(Text, nullable=False)
    recommendations_json = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
