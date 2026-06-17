from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.tokens import create_access_token

SECRET = "test-jwt-secret"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, username: str, password: str) -> object:
    return client.post(
        "/v1/auth/login", json={"username": username, "password": password}
    )


def _model_payload() -> dict[str, object]:
    return {
        "name": "fraud-model",
        "version": "v1",
        "artifact_path": "artifacts/missing.joblib",
        "training_dataset": "synthetic",
        "metrics": {},
    }


def _create_user(
    client: TestClient, admin_headers: dict[str, str], username: str, role: str
) -> object:
    return client.post(
        "/v1/auth/users",
        headers=admin_headers,
        json={"username": username, "password": "password123", "role": role},
    )


def test_login_success(client: TestClient) -> None:
    """Valid credentials should return a bearer token with the user's role."""

    response = _login(client, "admin", "admin-password")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "admin"
    assert body["access_token"]


def test_login_invalid_credentials_returns_401(client: TestClient) -> None:
    """Wrong password or unknown user should be rejected."""

    assert _login(client, "admin", "wrong").status_code == 401
    assert _login(client, "ghost", "whatever").status_code == 401


def test_admin_token_can_manage_models(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """A valid admin token should be allowed to register a model."""

    response = client.post("/v1/models", headers=admin_headers, json=_model_payload())
    assert response.status_code == 201


def test_service_user_can_predict_but_not_manage_models(
    client: TestClient,
    admin_headers: dict[str, str],
    sample_transaction: dict[str, object],
) -> None:
    """The service role can score transactions but not manage models."""

    assert _create_user(client, admin_headers, "svc", "service").status_code == 201
    token = _login(client, "svc", "password123").json()["access_token"]
    headers = _bearer(token)

    assert client.post(
        "/v1/transactions/score", headers=headers, json=sample_transaction
    ).status_code == 201
    assert client.post("/v1/models", headers=headers, json=_model_payload()).status_code == 403


def test_analyst_role_is_read_only(
    client: TestClient,
    admin_headers: dict[str, str],
    sample_transaction: dict[str, object],
) -> None:
    """The analyst role can read analytics but cannot predict or manage models."""

    assert _create_user(client, admin_headers, "ana", "analyst").status_code == 201
    token = _login(client, "ana", "password123").json()["access_token"]
    headers = _bearer(token)

    assert client.get("/v1/metrics/model", headers=headers).status_code == 200
    assert client.post(
        "/v1/transactions/score", headers=headers, json=sample_transaction
    ).status_code == 403
    assert client.post("/v1/models", headers=headers, json=_model_payload()).status_code == 403


def test_invalid_token_returns_401(client: TestClient) -> None:
    """A malformed bearer token should be rejected."""

    assert client.get("/v1/metrics/model", headers=_bearer("not-a-jwt")).status_code == 401


def test_expired_token_returns_401(client: TestClient) -> None:
    """An expired token should be rejected."""

    issued = datetime.now(UTC) - timedelta(hours=2)
    token = create_access_token(
        subject="admin",
        role="admin",
        secret=SECRET,
        algorithm="HS256",
        issued_at=issued,
        expires_minutes=1,
    )
    assert client.get("/v1/metrics/model", headers=_bearer(token)).status_code == 401


def test_api_key_acts_as_service_role(
    client: TestClient,
    auth_headers: dict[str, str],
    sample_transaction: dict[str, object],
) -> None:
    """The static API key authenticates a service account: predict yes, manage no."""

    assert client.post(
        "/v1/transactions/score", headers=auth_headers, json=sample_transaction
    ).status_code == 201
    assert client.post("/v1/models", headers=auth_headers, json=_model_payload()).status_code == 403


def test_user_creation_requires_admin(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    """User creation is admin-only; service users and anonymous callers are denied."""

    # Anonymous request.
    assert client.post(
        "/v1/auth/users",
        json={"username": "x", "password": "password123", "role": "analyst"},
    ).status_code == 401

    # Service-role token.
    _create_user(client, admin_headers, "svc2", "service")
    token = _login(client, "svc2", "password123").json()["access_token"]
    assert client.post(
        "/v1/auth/users",
        headers=_bearer(token),
        json={"username": "y", "password": "password123", "role": "analyst"},
    ).status_code == 403
