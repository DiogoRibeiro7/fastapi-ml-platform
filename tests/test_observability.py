from fastapi.testclient import TestClient


def test_metrics_endpoint_returns_prometheus_format(client: TestClient) -> None:
    """The /metrics endpoint should return Prometheus text exposition format."""

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "version=" in response.headers["content-type"]
    assert "http_request_duration_seconds" in response.text


def test_request_metrics_are_recorded(client: TestClient) -> None:
    """HTTP request count should be labeled by route, method, and status."""

    client.get("/health")
    body = client.get("/metrics").text

    assert "http_requests_total" in body
    assert 'endpoint="/health"' in body
    assert 'method="GET"' in body


def test_prediction_metrics_are_recorded(
    client: TestClient,
    auth_headers: dict[str, str],
    sample_transaction: dict[str, object],
) -> None:
    """Scoring should record prediction latency and risk/decision counts."""

    response = client.post(
        "/v1/transactions/score", headers=auth_headers, json=sample_transaction
    )
    risk_level = response.json()["risk_level"]

    body = client.get("/metrics").text

    assert "model_prediction_duration_seconds" in body
    assert "model_predictions_total" in body
    assert f'risk_level="{risk_level}"' in body


def test_metrics_endpoint_is_unauthenticated(client: TestClient) -> None:
    """The metrics endpoint should be scrapable without an API key."""

    assert client.get("/metrics").status_code == 200
