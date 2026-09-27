"""The Alembic migration must build exactly the schema the ORM models describe."""

import os
import subprocess
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401
from app.core.database import Base

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_matches_models(tmp_path):
    url = os.environ.get("MIGRATION_TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'migrate.db'}")
    env = {**os.environ, "DATABASE_URL": url}
    for command in (["upgrade", "head"], ["downgrade", "base"], ["upgrade", "head"]):
        result = subprocess.run([sys.executable, "-m", "alembic", *command], cwd=BACKEND, env=env,  # noqa: S603
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    engine = create_engine(url)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        tables = set(inspect(connection).get_table_names())
    assert set(Base.metadata.tables) <= tables
    assert diff == [], diff
