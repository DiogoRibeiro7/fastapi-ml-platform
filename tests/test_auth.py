from fastapi.testclient import TestClient


def test_protected_endpoint_requires_api_key(client: TestClient) -> None:
    """Protected endpoints should reject missing API keys."""

    response = client.get("/v1/models/current")

    assert response.status_code == 401


def test_protected_endpoint_rejects_invalid_api_key(client: TestClient) -> None:
    """Protected endpoints should reject invalid API keys."""

    response = client.get("/v1/models/current", headers={"X-API-Key": "wrong"})

    assert response.status_code == 403
