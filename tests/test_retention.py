from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import DeadLetter, DriftReport, PredictionLog
from app.db.session import build_session_factory, create_database_tables, dispose_engine
from app.services.retention_service import RetentionService


def _prediction(transaction_id: str, created_at: datetime) -> PredictionLog:
    return PredictionLog(
        transaction_id=transaction_id,
        customer_id="c1",
        risk_score=0.5,
        risk_level="medium",
        decision="review",
        model_version="v1",
        features={},
        request_payload={},
        top_features=[],
        created_at=created_at,
    )


async def test_purge_deletes_old_records_keeps_recent(tmp_path: Path) -> None:
    """Records older than the window are deleted; recent ones are kept."""

    engine, session_factory = build_session_factory(
        f"sqlite+aiosqlite:///{tmp_path / 'r.db'}"
    )
    await create_database_tables(engine)
    old = datetime.now(UTC) - timedelta(days=100)
    recent = datetime.now(UTC) - timedelta(days=1)

    try:
        async with session_factory() as session:
            session.add_all(
                [
                    _prediction("old", old),
                    _prediction("recent", recent),
                    DriftReport(
                        id="old", generated_at=old, sample_size=0,
                        max_severity="none", summary="s", features=[],
                    ),
                    DriftReport(
                        id="recent", generated_at=recent, sample_size=0,
                        max_severity="none", summary="s", features=[],
                    ),
                    DeadLetter(
                        job_id="j", transaction_id="old", payload={},
                        error="e", created_at=old,
                    ),
                ]
            )
            await session.commit()

            deleted = await RetentionService(session).purge(retention_days=30)

            assert deleted == {
                "prediction_logs": 1,
                "drift_reports": 1,
                "dead_letters": 1,
            }
            remaining = await session.execute(select(func.count()).select_from(PredictionLog))
            assert remaining.scalar_one() == 1
    finally:
        await dispose_engine(engine)


def test_retention_cleanup_endpoint_requires_admin(
    client: TestClient,
    auth_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    """The cleanup endpoint is admin-only and runs with an explicit window."""

    # Service role (API key) is denied.
    assert client.post(
        "/v1/admin/retention/cleanup", headers=auth_headers, params={"days": 30}
    ).status_code == 403

    # Admin succeeds and receives per-table deletion counts.
    response = client.post(
        "/v1/admin/retention/cleanup", headers=admin_headers, params={"days": 30}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["retention_days"] == 30
    assert set(body["deleted"]) == {"prediction_logs", "drift_reports", "dead_letters"}


def test_retention_cleanup_unconfigured_returns_400(
    client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    """Without a configured window and no override, cleanup is a 400."""

    response = client.post("/v1/admin/retention/cleanup", headers=admin_headers)
    assert response.status_code == 400
