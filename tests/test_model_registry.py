from pathlib import Path

from fastapi.testclient import TestClient

from app.ml.training import train_baseline_model


def _registration_payload(
    version: str = "v1",
    artifact_path: str = "artifacts/missing.joblib",
) -> dict[str, object]:
    return {
        "name": "fraud-model",
        "version": version,
        "artifact_path": artifact_path,
        "training_dataset": "synthetic-2026-06",
        "metrics": {"roc_auc": 0.91},
    }


def _train_artifact(directory: Path, version: str) -> Path:
    """Train a small real model artifact and return its path."""

    artifact_path = directory / f"model_{version}.joblib"
    train_baseline_model(artifact_path, artifact_path.with_suffix(".json"), n_samples=600)
    return artifact_path


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
    tmp_path: Path,
) -> None:
    """Activating a model should deactivate any previously active model."""

    path_v1 = _train_artifact(tmp_path, "v1")
    path_v2 = _train_artifact(tmp_path, "v2")
    first = client.post(
        "/v1/models", headers=auth_headers, json=_registration_payload("v1", str(path_v1))
    ).json()
    second = client.post(
        "/v1/models", headers=auth_headers, json=_registration_payload("v2", str(path_v2))
    ).json()

    response = client.post(f"/v1/models/{first['id']}/activate", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is True

    response = client.post(f"/v1/models/{second['id']}/activate", headers=auth_headers)
    assert response.status_code == 200

    models = client.get("/v1/models", headers=auth_headers).json()["models"]
    active_ids = [model["id"] for model in models if model["is_active"]]
    assert active_ids == [second["id"]]


def test_activation_hot_swaps_served_model(
    client: TestClient,
    auth_headers: dict[str, str],
    tmp_path: Path,
) -> None:
    """Promoting a model should change the model served by the API."""

    # The default served model is the rule-based fallback.
    current = client.get("/v1/models/current", headers=auth_headers).json()
    assert current["version"] == "rule-based-v1"

    artifact = _train_artifact(tmp_path, "v1")
    registered = client.post(
        "/v1/models", headers=auth_headers, json=_registration_payload("v1", str(artifact))
    ).json()

    activate = client.post(f"/v1/models/{registered['id']}/activate", headers=auth_headers)
    assert activate.status_code == 200

    # The served model identity comes from the registry row, not the artifact.
    current = client.get("/v1/models/current", headers=auth_headers).json()
    assert current["version"] == "v1"
    assert current["name"] == "fraud-model"
    ready = client.get("/ready")
    assert ready.json()["model_version"] == "v1"


def test_activate_missing_artifact_returns_422(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Promoting a model whose artifact cannot be loaded should return 422."""

    registered = client.post(
        "/v1/models",
        headers=auth_headers,
        json=_registration_payload("v1", "artifacts/does_not_exist.joblib"),
    ).json()

    response = client.post(f"/v1/models/{registered['id']}/activate", headers=auth_headers)

    assert response.status_code == 422

    # The failed promotion must not flip the active flag.
    models = client.get("/v1/models", headers=auth_headers).json()["models"]
    assert all(model["is_active"] is False for model in models)


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
