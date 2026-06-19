import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

POSTGRES_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.mark.skipif(POSTGRES_URL is None, reason="TEST_DATABASE_URL is not set")
def test_postgres_score_and_retrieve(
    api_key: str,
    auth_headers: dict[str, str],
    sample_transaction: dict[str, object],
    tmp_path: Path,
) -> None:
    """The app should score and persist a prediction against real PostgreSQL.

    Exercises the asyncpg driver and JSON/timestamp columns on the production
    database engine, which the SQLite-based suite does not cover.
    """

    settings = Settings(
        api_key=api_key,
        database_url=POSTGRES_URL or "",
        model_artifact_path=tmp_path / "missing.joblib",
        model_metadata_path=tmp_path / "missing.json",
        train_baseline_if_missing=False,
        process_jobs_inline=True,
        bootstrap_admin_username=None,
        rate_limit_requests=100_000,
    )
    app = create_app(settings=settings)

    transaction = dict(sample_transaction)
    transaction["transaction_id"] = f"pg_{uuid.uuid4().hex}"

    with TestClient(app) as client:
        scored = client.post(
            "/v1/transactions/score", headers=auth_headers, json=transaction
        )
        assert scored.status_code == 201
        transaction_id = scored.json()["transaction_id"]

        fetched = client.get(
            f"/v1/transactions/{transaction_id}", headers=auth_headers
        )
        assert fetched.status_code == 200
        assert fetched.json()["transaction_id"] == transaction_id
