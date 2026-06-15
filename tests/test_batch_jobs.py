from fastapi.testclient import TestClient


def _transactions(count: int) -> list[dict[str, object]]:
    return [
        {
            "transaction_id": f"txn_{i}",
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
        for i in range(count)
    ]


def test_submit_batch_job_returns_accepted(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Submitting a job should return 202 with a job id and total."""

    response = client.post(
        "/v1/transactions/batch-score-jobs",
        headers=auth_headers,
        json={"transactions": _transactions(3)},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["id"]
    assert payload["total"] == 3
    assert payload["status"] in {"queued", "running", "completed"}


def test_job_completes_and_reports_result(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """An inline-processed job should complete with a result summary."""

    job_id = client.post(
        "/v1/transactions/batch-score-jobs",
        headers=auth_headers,
        json={"transactions": _transactions(4)},
    ).json()["id"]

    response = client.get(f"/v1/jobs/{job_id}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["completed"] == 4
    assert payload["finished_at"] is not None
    total_scored = sum(payload["result"]["decision_counts"].values())
    assert total_scored == 4


def test_batch_job_persists_predictions(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Scored transactions from a job should be retrievable like any prediction."""

    client.post(
        "/v1/transactions/batch-score-jobs",
        headers=auth_headers,
        json={"transactions": _transactions(2)},
    )

    response = client.get("/v1/transactions/txn_0", headers=auth_headers)
    assert response.status_code == 200


def test_get_unknown_job_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Fetching an unknown job id should return 404."""

    response = client.get("/v1/jobs/does-not-exist", headers=auth_headers)

    assert response.status_code == 404


def test_batch_job_requires_api_key(client: TestClient) -> None:
    """The batch-job endpoints should require authentication."""

    assert client.post(
        "/v1/transactions/batch-score-jobs", json={"transactions": _transactions(1)}
    ).status_code == 401
    assert client.get("/v1/jobs/whatever").status_code == 401
