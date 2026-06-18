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


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin-password"


@pytest.fixture()
def client(tmp_path: Path, api_key: str) -> Iterator[TestClient]:
    """Create a test client with an isolated SQLite database."""

    database_path = tmp_path / "test.db"
    settings = Settings(
        api_key=api_key,
        database_url=f"sqlite+aiosqlite:///{database_path}",
        model_artifact_path=tmp_path / "missing_model.joblib",
        model_metadata_path=tmp_path / "missing_metadata.json",
        train_baseline_if_missing=False,
        process_jobs_inline=True,
        jwt_secret="test-jwt-secret",
        bootstrap_admin_username=ADMIN_USERNAME,
        bootstrap_admin_password=ADMIN_PASSWORD,
        rate_limit_requests=100_000,
    )
    app = create_app(settings=settings)

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(api_key: str) -> dict[str, str]:
    """Return API-key headers (service role) for protected endpoints."""

    return {"X-API-Key": api_key}


@pytest.fixture()
def admin_headers(client: TestClient) -> dict[str, str]:
    """Log in as the bootstrap admin and return bearer-token headers."""

    response = client.post(
        "/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


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
