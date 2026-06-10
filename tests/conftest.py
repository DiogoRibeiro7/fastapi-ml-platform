from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture()
def api_key() -> str:
    """Return the test API key."""

    return "test-api-key"


@pytest.fixture()
def client(tmp_path: Path, api_key: str) -> Iterator[TestClient]:
    """Create a test client with an isolated SQLite database."""

    database_path = tmp_path / "test.db"
    settings = Settings(
        api_key=api_key,
        database_url=f"sqlite+aiosqlite:///{database_path}",
        model_artifact_path=tmp_path / "missing_model.joblib",
        model_metadata_path=tmp_path / "missing_metadata.json",
    )
    app = create_app(settings=settings)

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(api_key: str) -> dict[str, str]:
    """Return authentication headers for protected endpoints."""

    return {"X-API-Key": api_key}


@pytest.fixture()
def sample_transaction() -> dict[str, object]:
    """Return a valid transaction payload."""

    return {
        "transaction_id": "txn_test_001",
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
