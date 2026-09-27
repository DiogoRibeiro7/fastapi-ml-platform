"""Failure contracts for loading the persisted model and its metadata."""

from pathlib import Path

import joblib
import pytest
from dataexcept import FileReadError, ModelSerializationError

from app.ml.model_loader import load_model_bundle, load_registered_bundle


def test_missing_registered_artifact_has_path_and_cause(tmp_path: Path) -> None:
    """A registered model cannot silently fall back when its artifact is gone."""
    artifact = tmp_path / "missing.joblib"

    with pytest.raises(FileReadError) as caught:
        load_registered_bundle(artifact, name="fraud", version="v1", metrics={})

    assert caught.value.path == str(artifact)
    assert isinstance(caught.value.original, FileNotFoundError)
    assert caught.value.__cause__ is caught.value.original


def test_corrupt_registered_artifact_preserves_deserialization_error(tmp_path: Path) -> None:
    """Corrupt serialized bytes identify the artifact and retain the cause."""
    artifact = tmp_path / "broken.joblib"
    artifact.write_bytes(b"not a joblib artifact")

    with pytest.raises(ModelSerializationError) as caught:
        load_registered_bundle(artifact, name="fraud", version="v1", metrics={})

    assert caught.value.path == str(artifact)
    assert caught.value.__cause__ is caught.value.original


def test_registered_artifact_must_provide_probability_predictions(tmp_path: Path) -> None:
    """A valid joblib file without the serving interface is still unusable."""
    artifact = tmp_path / "wrong-interface.joblib"
    joblib.dump({"not": "a model"}, artifact)

    with pytest.raises(ModelSerializationError) as caught:
        load_registered_bundle(artifact, name="fraud", version="v1", metrics={})

    assert isinstance(caught.value.original, TypeError)
    assert caught.value.__cause__ is caught.value.original


def test_invalid_metadata_identifies_file_without_masking_parse_error(tmp_path: Path) -> None:
    """Malformed optional metadata fails visibly when the file exists."""
    metadata = tmp_path / "metadata.json"
    metadata.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(FileReadError) as caught:
        load_model_bundle(tmp_path / "missing.joblib", metadata)

    assert caught.value.path == str(metadata)
    assert isinstance(caught.value.original, ValueError)
    assert caught.value.__cause__ is caught.value.original
