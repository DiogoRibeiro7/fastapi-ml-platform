import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.ingestion_service import parse_transaction_records


def _transaction(txn_id: str) -> dict[str, object]:
    return {
        "transaction_id": txn_id,
        "customer_id": "customer_001",
        "amount": 450.0,
        "merchant_category": "electronics",
        "merchant_country": "PT",
        "card_country": "PT",
        "hour_of_day": 2,
        "day_of_week": 5,
        "is_card_present": False,
        "customer_age_days": 45,
        "num_transactions_last_24h": 12,
        "avg_amount_last_7d": 55.0,
        "chargeback_count_last_90d": 1,
    }


def test_parse_json_array() -> None:
    """A JSON array payload should parse into a list of records."""

    raw = json.dumps([_transaction("a"), _transaction("b")]).encode("utf-8")
    assert len(parse_transaction_records(raw)) == 2


def test_parse_json_lines() -> None:
    """Newline-delimited JSON should parse into one record per line."""

    raw = (
        json.dumps(_transaction("a")) + "\n" + json.dumps(_transaction("b")) + "\n"
    ).encode("utf-8")
    assert len(parse_transaction_records(raw)) == 2


def test_parse_single_object() -> None:
    """A single JSON object should parse into a one-record list."""

    assert len(parse_transaction_records(json.dumps(_transaction("a")).encode())) == 1


def test_parse_empty_is_empty() -> None:
    """An empty payload should parse to an empty list."""

    assert parse_transaction_records(b"   ") == []


def test_parse_rejects_non_object_json() -> None:
    """A bare JSON scalar is not a valid transaction payload."""

    with pytest.raises(ValueError, match="JSON object"):
        parse_transaction_records(b"42")


def test_ingest_array_creates_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Ingesting a JSON array should create and complete a batch job."""

    raw = json.dumps([_transaction("ing_1"), _transaction("ing_2")])
    response = client.post("/v1/transactions/ingest", headers=auth_headers, content=raw)

    assert response.status_code == 202
    job_id = response.json()["id"]
    job = client.get(f"/v1/jobs/{job_id}", headers=auth_headers).json()
    assert job["status"] == "completed"
    assert job["result"]["scored"] == 2


def test_ingest_json_lines_creates_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Ingesting newline-delimited JSON should also create a job."""

    raw = "\n".join(json.dumps(_transaction(f"jl_{i}")) for i in range(3))
    response = client.post("/v1/transactions/ingest", headers=auth_headers, content=raw)

    assert response.status_code == 202
    assert response.json()["total"] == 3


def test_ingest_invalid_transaction_returns_422(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """A record missing required fields should fail ingestion validation."""

    raw = json.dumps([{"customer_id": "c1"}])
    response = client.post("/v1/transactions/ingest", headers=auth_headers, content=raw)

    assert response.status_code == 422


def test_ingest_empty_payload_returns_422(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """An empty payload should be rejected."""

    response = client.post("/v1/transactions/ingest", headers=auth_headers, content="")
    assert response.status_code == 422


def test_ingest_too_many_records_returns_413(
    tmp_path: Path,
    api_key: str,
    auth_headers: dict[str, str],
) -> None:
    """A payload exceeding max_ingest_records should return 413."""

    settings = Settings(
        api_key=api_key,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        model_artifact_path=tmp_path / "missing.joblib",
        model_metadata_path=tmp_path / "missing.json",
        train_baseline_if_missing=False,
        process_jobs_inline=True,
        max_ingest_records=2,
    )
    app = create_app(settings=settings)
    raw = json.dumps([_transaction(f"x_{i}") for i in range(3)])

    with TestClient(app) as client:
        response = client.post("/v1/transactions/ingest", headers=auth_headers, content=raw)

    assert response.status_code == 413


def test_ingest_requires_api_key(client: TestClient) -> None:
    """Ingestion should require authentication."""

    assert client.post("/v1/transactions/ingest", content="[]").status_code == 401
