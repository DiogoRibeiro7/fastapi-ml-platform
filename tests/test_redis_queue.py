import asyncio
from pathlib import Path

from fakeredis import FakeStrictRedis
from rq import Queue, SimpleWorker

from app.core.config import Settings
from app.core.redis_queue import RedisBatchDispatcher
from app.db.session import build_session_factory, create_database_tables, dispose_engine
from app.repositories.batch_job_repository import BatchJobRepository
from app.schemas.prediction import TransactionInput


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
