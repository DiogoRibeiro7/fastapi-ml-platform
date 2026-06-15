import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ml.training import train_baseline_model


@pytest.fixture()
def audit_records() -> Iterator[list[logging.LogRecord]]:
    """Capture records emitted on the audit logger during a test."""

    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    audit_logger = logging.getLogger("audit")
    audit_logger.addHandler(handler)
    try:
        yield records
    finally:
        audit_logger.removeHandler(handler)


def test_missing_api_key_emits_audit_event(
    client: TestClient,
    audit_records: list[logging.LogRecord],
) -> None:
    """A missing API key should produce a denied auth audit event."""

    client.get("/v1/models/current")

    auth_events = [r for r in audit_records if r.action == "auth_failed"]
    assert auth_events
    event = auth_events[-1]
    assert event.outcome == "denied"
    assert event.reason == "missing_api_key"
    assert event.path == "/v1/models/current"


def test_invalid_api_key_audit_reason(
    client: TestClient,
    audit_records: list[logging.LogRecord],
) -> None:
    """An invalid API key should be recorded with the invalid reason."""

    client.get("/v1/models/current", headers={"X-API-Key": "wrong"})

    event = next(r for r in audit_records if r.action == "auth_failed")
    assert event.reason == "invalid_api_key"


def test_successful_auth_emits_no_audit_event(
    client: TestClient,
    auth_headers: dict[str, str],
    audit_records: list[logging.LogRecord],
) -> None:
    """A valid key should not raise an auth-failure audit event."""

    client.get("/v1/models/current", headers=auth_headers)

    assert not [r for r in audit_records if r.action == "auth_failed"]


def test_model_registration_emits_audit_event(
    client: TestClient,
    auth_headers: dict[str, str],
    audit_records: list[logging.LogRecord],
) -> None:
    """Registering a model should produce a model_registered audit event."""

    client.post(
        "/v1/models",
        headers=auth_headers,
        json={
            "name": "fraud-model",
            "version": "v1",
            "artifact_path": "artifacts/missing.joblib",
            "training_dataset": "synthetic",
            "metrics": {},
        },
    )

    event = next(r for r in audit_records if r.action == "model_registered")
    assert event.outcome == "success"
    assert event.version == "v1"


def test_model_promotion_emits_audit_event(
    client: TestClient,
    auth_headers: dict[str, str],
    audit_records: list[logging.LogRecord],
    tmp_path: Path,
) -> None:
    """Promoting a model should produce a model_promoted audit event."""

    artifact = tmp_path / "model.joblib"
    train_baseline_model(artifact, artifact.with_suffix(".json"), n_samples=600)
    registered = client.post(
        "/v1/models",
        headers=auth_headers,
        json={
            "name": "fraud-model",
            "version": "v1",
            "artifact_path": str(artifact),
            "training_dataset": "synthetic",
            "metrics": {},
        },
    ).json()

    client.post(f"/v1/models/{registered['id']}/activate", headers=auth_headers)

    event = next(r for r in audit_records if r.action == "model_promoted")
    assert event.outcome == "success"
    assert event.model_id == registered["id"]
