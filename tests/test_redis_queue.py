import asyncio
from pathlib import Path

import pytest
from fakeredis import FakeStrictRedis
from rq import Queue, SimpleWorker

from app.core.config import Settings
from app.core.correlation import get_request_id, reset_request_id, set_request_id
from app.core.redis_queue import RedisBatchDispatcher
from app.db.session import build_session_factory, create_database_tables, dispose_engine
from app.repositories.batch_job_repository import BatchJobRepository
from app.schemas.prediction import TransactionInput
from app.services import batch_tasks


def _transaction(txn_id: str) -> dict[str, object]:
    return {
        "transaction_id": txn_id,
        "customer_id": "customer_001",
        "amount": 450.0,
        "merchant_category": "electronics",
        "merchant_country": "PT",
        "card_country": "PT",
        "hour_of_day": 2,
        "day_of_week": 5,
        "is_card_present": False,
        "customer_age_days": 45,
        "num_transactions_last_24h": 12,
        "avg_amount_last_7d": 55.0,
        "chargeback_count_last_90d": 1,
    }


async def _create_tables_and_job(db_url: str, job_id: str, total: int) -> None:
    engine, session_factory = build_session_factory(db_url)
    await create_database_tables(engine)
    async with session_factory() as session:
        await BatchJobRepository(session).create(job_id=job_id, total=total)
    await dispose_engine(engine)


async def _read_job(db_url: str, job_id: str) -> tuple[str, dict[str, object] | None]:
    engine, session_factory = build_session_factory(db_url)
    async with session_factory() as session:
        row = await BatchJobRepository(session).get(job_id)
        result = (row.status, row.result) if row is not None else ("missing", None)
    await dispose_engine(engine)
    return result


def test_redis_backend_processes_batch_job(tmp_path: Path) -> None:
    """A job dispatched to RQ is executed by a worker and marked completed.

    This is a synchronous test so the worker's asyncio.run is not nested inside
    a running event loop. Each async step uses its own engine to avoid sharing
    an aiosqlite connection across event loops.
    """

    db_url = f"sqlite+aiosqlite:///{tmp_path / 'r.db'}"
    settings = Settings(
        database_url=db_url,
        model_artifact_path=tmp_path / "missing.joblib",
        model_metadata_path=tmp_path / "missing.json",
        train_baseline_if_missing=False,
        job_backend="redis",
    )

    asyncio.run(_create_tables_and_job(db_url, "job-1", total=2))

    connection = FakeStrictRedis()
    queue = Queue(connection=connection)
    transactions = [
        TransactionInput.model_validate(_transaction("r1")),
        TransactionInput.model_validate(_transaction("r2")),
    ]
    asyncio.run(RedisBatchDispatcher(queue, settings).dispatch("job-1", transactions))

    # Nothing has run yet: the job is still queued in (fake) Redis.
    assert queue.count == 1

    SimpleWorker([queue], connection=connection).work(burst=True)

    status, result = asyncio.run(_read_job(db_url, "job-1"))
    assert status == "completed"
    assert result is not None
    assert result["scored"] == 2


def test_redis_dispatch_enqueues_without_running(tmp_path: Path) -> None:
    """Dispatching enqueues a job but does not execute it inline."""

    settings = Settings(database_url="sqlite+aiosqlite:///x.db", job_backend="redis")
    queue = Queue(connection=FakeStrictRedis())

    asyncio.run(
        RedisBatchDispatcher(queue, settings).dispatch(
            "job-2", [TransactionInput.model_validate(_transaction("a"))]
        )
    )

    assert queue.count == 1
    enqueued = queue.jobs[0]
    assert enqueued.func_name.endswith("run_batch_job_task")


def test_dispatch_captures_current_correlation_id(tmp_path: Path) -> None:
    """The dispatcher should attach the request's correlation id to the job."""

    settings = Settings(database_url="sqlite+aiosqlite:///x.db", job_backend="redis")
    queue = Queue(connection=FakeStrictRedis())

    token = set_request_id("trace-abc")
    try:
        asyncio.run(
            RedisBatchDispatcher(queue, settings).dispatch(
                "job-3", [TransactionInput.model_validate(_transaction("a"))]
            )
        )
    finally:
        reset_request_id(token)

    assert queue.jobs[0].args[-1] == "trace-abc"


def test_worker_restores_correlation_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worker task should restore the correlation id while scoring, then reset."""

    captured: dict[str, str] = {}

    async def fake_process_job(*args: object, **kwargs: object) -> None:
        captured["request_id"] = get_request_id()

    monkeypatch.setattr(batch_tasks, "_process_job", fake_process_job)

    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'w.db'}",
        model_artifact_path=tmp_path / "missing.joblib",
        model_metadata_path=tmp_path / "missing.json",
        train_baseline_if_missing=False,
    )

    batch_tasks.run_batch_job_task("job-4", [], settings, "trace-xyz")

    assert captured["request_id"] == "trace-xyz"
    assert get_request_id() == "-"  # context restored after the task
