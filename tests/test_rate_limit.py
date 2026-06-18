from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.rate_limit import RateLimiter
from app.main import create_app


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_rate_limiter_allows_up_to_limit_then_blocks() -> None:
    """The limiter should allow up to max requests, then deny within the window."""

    clock = _FakeClock()
    limiter = RateLimiter(max_requests=2, window_seconds=60, clock=clock)

    assert limiter.check("c").allowed is True
    assert limiter.check("c").allowed is True
    blocked = limiter.check("c")
    assert blocked.allowed is False
    assert blocked.retry_after > 0


def test_rate_limiter_resets_after_window() -> None:
    """After the window elapses, the client is allowed again."""

    clock = _FakeClock()
    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=clock)

    assert limiter.check("c").allowed is True
    assert limiter.check("c").allowed is False

    clock.now = 60.0
    assert limiter.check("c").allowed is True


def test_rate_limiter_isolates_clients() -> None:
    """Each client has an independent budget."""

    limiter = RateLimiter(max_requests=1, window_seconds=60, clock=_FakeClock())

    assert limiter.check("a").allowed is True
    assert limiter.check("b").allowed is True
    assert limiter.check("a").allowed is False


def _rate_limited_client(tmp_path: Path, api_key: str, limit: int) -> TestClient:
    settings = Settings(
        api_key=api_key,
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        model_artifact_path=tmp_path / "missing.joblib",
        model_metadata_path=tmp_path / "missing.json",
        train_baseline_if_missing=False,
        rate_limit_requests=limit,
        rate_limit_window_seconds=60,
    )
    return TestClient(create_app(settings=settings))


def test_endpoint_returns_429_when_rate_limited(
    tmp_path: Path,
    api_key: str,
    auth_headers: dict[str, str],
) -> None:
    """Exceeding the per-client limit should return 429 with Retry-After."""

    with _rate_limited_client(tmp_path, api_key, limit=2) as client:
        assert client.get("/v1/metrics/model", headers=auth_headers).status_code == 200
        assert client.get("/v1/metrics/model", headers=auth_headers).status_code == 200
        blocked = client.get("/v1/metrics/model", headers=auth_headers)

    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_health_endpoint_is_not_rate_limited(
    tmp_path: Path,
    api_key: str,
) -> None:
    """Infrastructure endpoints are exempt from rate limiting."""

    with _rate_limited_client(tmp_path, api_key, limit=1) as client:
        for _ in range(5):
            assert client.get("/health").status_code == 200
