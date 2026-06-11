from fastapi.testclient import TestClient


def _registration_payload(version: str = "v1") -> dict[str, object]:
    return {
        "name": "fraud-model",
        "version": version,
        "artifact_path": f"artifacts/fraud_model_{version}.joblib",
        "training_dataset": "synthetic-2026-06",
        "metrics": {"roc_auc": 0.91},
    }


def test_register_model_starts_inactive(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Registering a model should persist it as inactive."""

    response = client.post("/v1/models", headers=auth_headers, json=_registration_payload())

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "fraud-model"
    assert payload["version"] == "v1"
    assert payload["is_active"] is False
    assert payload["metrics"] == {"roc_auc": 0.91}


def test_register_duplicate_version_conflicts(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Registering the same name and version twice should return 409."""

    client.post("/v1/models", headers=auth_headers, json=_registration_payload())
    response = client.post("/v1/models", headers=auth_headers, json=_registration_payload())

    assert response.status_code == 409


def test_list_models_returns_registered_models(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """The list endpoint should return every registered model."""

    client.post("/v1/models", headers=auth_headers, json=_registration_payload("v1"))
    client.post("/v1/models", headers=auth_headers, json=_registration_payload("v2"))

    response = client.get("/v1/models", headers=auth_headers)

    assert response.status_code == 200
    versions = {model["version"] for model in response.json()["models"]}
    assert versions == {"v1", "v2"}


def test_activate_model_is_exclusive(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Activating a model should deactivate any previously active model."""

    first = client.post(
        "/v1/models", headers=auth_headers, json=_registration_payload("v1")
    ).json()
    second = client.post(
        "/v1/models", headers=auth_headers, json=_registration_payload("v2")
    ).json()

    response = client.post(f"/v1/models/{first['id']}/activate", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is True

    response = client.post(f"/v1/models/{second['id']}/activate", headers=auth_headers)
    assert response.status_code == 200

    models = client.get("/v1/models", headers=auth_headers).json()["models"]
    active_ids = [model["id"] for model in models if model["is_active"]]
    assert active_ids == [second["id"]]


def test_activate_unknown_model_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Activating a nonexistent model id should return 404."""

    response = client.post("/v1/models/9999/activate", headers=auth_headers)

    assert response.status_code == 404


def test_current_model_endpoint_is_preserved(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """The registry endpoints must not break /v1/models/current."""

    response = client.get("/v1/models/current", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["version"] == "rule-based-v1"
