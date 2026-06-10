from fastapi.testclient import TestClient


def test_score_transaction_returns_prediction(
    client: TestClient,
    auth_headers: dict[str, str],
    sample_transaction: dict[str, object],
) -> None:
    """Scoring endpoint should return a valid prediction payload."""

    response = client.post(
        "/v1/transactions/score",
        headers=auth_headers,
        json=sample_transaction,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["transaction_id"] == "txn_test_001"
    assert 0.0 <= payload["risk_score"] <= 1.0
    assert payload["risk_level"] in {"low", "medium", "high", "critical"}
    assert payload["decision"] in {"approve", "review", "decline"}
    assert payload["top_features"]


def test_get_prediction_after_scoring(
    client: TestClient,
    auth_headers: dict[str, str],
    sample_transaction: dict[str, object],
) -> None:
    """A scored transaction should be retrievable by transaction id."""

    client.post("/v1/transactions/score", headers=auth_headers, json=sample_transaction)
    response = client.get("/v1/transactions/txn_test_001", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["transaction_id"] == "txn_test_001"


def test_batch_score_returns_predictions(
    client: TestClient,
    auth_headers: dict[str, str],
    sample_transaction: dict[str, object],
) -> None:
    """Batch endpoint should return one prediction per input transaction."""

    second_transaction = dict(sample_transaction)
    second_transaction["transaction_id"] = "txn_test_002"
    response = client.post(
        "/v1/transactions/batch-score",
        headers=auth_headers,
        json={"transactions": [sample_transaction, second_transaction]},
    )

    assert response.status_code == 201
    assert len(response.json()["predictions"]) == 2
