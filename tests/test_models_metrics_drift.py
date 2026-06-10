from fastapi.testclient import TestClient


def test_current_model_returns_metadata(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Model endpoint should return active model metadata."""

    response = client.get("/v1/models/current", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "rule-based-v1"
    assert "features" in payload


def test_metrics_before_predictions(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Metrics endpoint should handle empty prediction logs."""

    response = client.get("/v1/metrics/model", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["prediction_count"] == 0


def test_drift_report_returns_feature_results(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Drift endpoint should return a report even with no predictions."""

    response = client.get("/v1/drift/report", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["sample_size"] == 0
    assert payload["features"]
