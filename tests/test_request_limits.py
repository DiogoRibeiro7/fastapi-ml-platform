from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _client(tmp_path: Path, api_key: str, max_bytes: int) -> TestClient:
    settings = Settings(
        api_key=api_key,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        model_artifact_path=tmp_path / "missing.joblib",
        model_metadata_path=tmp_path / "missing.json",
        train_baseline_if_missing=False,
        max_request_bytes=max_bytes,
    )
    return TestClient(create_app(settings=settings))


def test_oversized_request_returns_413(
    tmp_path: Path,
    api_key: str,
    auth_headers: dict[str, str],
) -> None:
    """A request body larger than the limit should be rejected with 413."""

    with _client(tmp_path, api_key, max_bytes=50) as client:
        response = client.post(
            "/v1/transactions/ingest",
            headers=auth_headers,
            content="x" * 200,
        )

    assert response.status_code == 413


def test_request_within_limit_is_processed(
    tmp_path: Path,
    api_key: str,
    auth_headers: dict[str, str],
) -> None:
    """A small body should pass the size check (and reach normal handling)."""

    with _client(tmp_path, api_key, max_bytes=1_000_000) as client:
        response = client.post(
            "/v1/transactions/ingest",
            headers=auth_headers,
            content="[]",
        )

    # 422 (empty payload) means the request passed the size gate.
    assert response.status_code == 422


def test_get_request_without_body_is_unaffected(
    tmp_path: Path,
    api_key: str,
) -> None:
    """A bodyless request should never be blocked by the size limit."""

    with _client(tmp_path, api_key, max_bytes=10) as client:
        assert client.get("/health").status_code == 200
