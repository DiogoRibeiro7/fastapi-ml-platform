from pathlib import Path

import pytest
from dataexcept import FileWriteError, ModelSerializationError
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.ml.training import MODEL_VERSION, train_baseline_model


def test_train_baseline_model_persists_artifacts(tmp_path: Path) -> None:
    """Training should write the model artifact and metadata with metrics."""

    artifact_path = tmp_path / "model.joblib"
    metadata_path = tmp_path / "metadata.json"

    metadata = train_baseline_model(artifact_path, metadata_path, n_samples=2_000)

    assert artifact_path.exists()
    assert metadata_path.exists()
    assert metadata["version"] == MODEL_VERSION
    assert 0.5 < metadata["metrics"]["roc_auc"] <= 1.0


def test_training_reports_artifact_write_failure(tmp_path: Path) -> None:
    """A failed artifact save carries the destination and underlying error."""
    artifact = tmp_path / "existing-directory"
    artifact.mkdir()

    with pytest.raises(ModelSerializationError) as caught:
        train_baseline_model(artifact, tmp_path / "metadata.json", n_samples=600)

    assert caught.value.path == str(artifact)
    assert isinstance(caught.value.original, OSError)
    assert caught.value.__cause__ is caught.value.original


def test_training_reports_metadata_write_failure(tmp_path: Path) -> None:
    """A saved artifact does not conceal failure to persist its metadata."""
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("blocked", encoding="utf-8")
    artifact = tmp_path / "model.joblib"
    metadata = blocked / "metadata.json"

    with pytest.raises(FileWriteError) as caught:
        train_baseline_model(artifact, metadata, n_samples=600)

    assert artifact.exists()
    assert caught.value.path == str(metadata)
    assert isinstance(caught.value.original, OSError)
    assert caught.value.__cause__ is caught.value.original


def test_startup_trains_baseline_when_artifact_missing(
    tmp_path: Path,
    api_key: str,
    auth_headers: dict[str, str],
) -> None:
    """With training enabled, startup should serve a trained model by default."""

    settings = Settings(
        api_key=api_key,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        model_artifact_path=tmp_path / "fraud_model.joblib",
        model_metadata_path=tmp_path / "fraud_model_metadata.json",
        train_baseline_if_missing=True,
    )
    app = create_app(settings=settings)

    with TestClient(app) as client:
        response = client.get("/v1/models/current", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == MODEL_VERSION
    assert settings.model_artifact_path.exists()
