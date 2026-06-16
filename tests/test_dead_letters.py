import pytest
from fastapi.testclient import TestClient

from app.schemas.prediction import PredictionResponse, TransactionInput
from app.services.prediction_service import PredictionService


def _transaction(txn_id: str, customer_id: str = "customer_001") -> dict[str, object]:
    return {
        "transaction_id": txn_id,
        "customer_id": customer_id,
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


@pytest.fixture()
def fail_boom_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make scoring raise for any transaction whose customer_id is 'boom'."""

    original = PredictionService.score_transaction

    async def flaky(
        self: PredictionService, transaction: TransactionInput
    ) -> PredictionResponse:
        if transaction.customer_id == "boom":
            raise RuntimeError("scoring exploded")
        return await original(self, transaction)

    monkeypatch.setattr(PredictionService, "score_transaction", flaky)


def test_bad_transaction_is_dead_lettered_others_succeed(
    client: TestClient,
    auth_headers: dict[str, str],
    fail_boom_transactions: None,
) -> None:
    """A failing transaction should be dead-lettered while the rest complete."""

    job_id = client.post(
        "/v1/transactions/batch-score-jobs",
        headers=auth_headers,
        json={
            "transactions": [
                _transaction("ok_1"),
                _transaction("bad_1", customer_id="boom"),
                _transaction("ok_2"),
            ]
        },
    ).json()["id"]

    job = client.get(f"/v1/jobs/{job_id}", headers=auth_headers).json()
    assert job["status"] == "completed"
    assert job["result"]["scored"] == 2
    assert job["result"]["failed"] == 1

    dead = client.get(f"/v1/jobs/{job_id}/dead-letters", headers=auth_headers).json()
    assert len(dead["dead_letters"]) == 1
    entry = dead["dead_letters"][0]
    assert entry["transaction_id"] == "bad_1"
    assert "exploded" in entry["error"]


def test_dead_letters_empty_for_clean_job(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """A job with no failures should report no dead letters."""

    job_id = client.post(
        "/v1/transactions/batch-score-jobs",
        headers=auth_headers,
        json={"transactions": [_transaction("ok_1")]},
    ).json()["id"]

    dead = client.get(f"/v1/jobs/{job_id}/dead-letters", headers=auth_headers).json()
    assert dead["dead_letters"] == []


def test_retry_dead_letters_creates_new_job(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retrying dead letters should resubmit them, succeeding once scoring works."""

    original = PredictionService.score_transaction
    fail = {"on": True}

    async def flaky(
        self: PredictionService, transaction: TransactionInput
    ) -> PredictionResponse:
        if fail["on"] and transaction.customer_id == "boom":
            raise RuntimeError("scoring exploded")
        return await original(self, transaction)

    monkeypatch.setattr(PredictionService, "score_transaction", flaky)

    first_job = client.post(
        "/v1/transactions/batch-score-jobs",
        headers=auth_headers,
        json={"transactions": [_transaction("bad_1", customer_id="boom")]},
    ).json()["id"]
    assert client.get(f"/v1/jobs/{first_job}", headers=auth_headers).json()["result"]["failed"] == 1

    # The failure is resolved; the retry should now succeed.
    fail["on"] = False
    retry = client.post(
        f"/v1/jobs/{first_job}/retry-dead-letters", headers=auth_headers
    )
    assert retry.status_code == 202
    retry_job_id = retry.json()["id"]

    retried = client.get(f"/v1/jobs/{retry_job_id}", headers=auth_headers).json()
    assert retried["status"] == "completed"
    assert retried["result"]["scored"] == 1
    assert retried["result"]["failed"] == 0


def test_retry_without_dead_letters_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Retrying a job with no dead letters should return 404."""

    job_id = client.post(
        "/v1/transactions/batch-score-jobs",
        headers=auth_headers,
        json={"transactions": [_transaction("ok_1")]},
    ).json()["id"]

    response = client.post(f"/v1/jobs/{job_id}/retry-dead-letters", headers=auth_headers)
    assert response.status_code == 404


def test_dead_letters_unknown_job_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Listing dead letters for an unknown job should return 404."""

    assert (
        client.get("/v1/jobs/nope/dead-letters", headers=auth_headers).status_code == 404
    )
