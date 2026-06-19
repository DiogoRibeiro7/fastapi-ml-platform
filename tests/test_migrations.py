import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

EXPECTED_TABLES = {
    "users",
    "prediction_logs",
    "model_registry",
    "drift_reports",
    "dead_letters",
    "batch_jobs",
}


def _table_names(db_path: Path) -> set[str]:
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    finally:
        connection.close()
    return {row[0] for row in rows}


def test_migrations_upgrade_creates_all_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`alembic upgrade head` should build the full schema from scratch."""

    db_path = tmp_path / "migrated.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    command.upgrade(Config("alembic.ini"), "head")

    tables = _table_names(db_path)
    assert EXPECTED_TABLES <= tables
    assert "alembic_version" in tables


def test_migrations_downgrade_removes_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Downgrading to base should drop the model tables."""

    db_path = tmp_path / "migrated.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    assert not (EXPECTED_TABLES & _table_names(db_path))
