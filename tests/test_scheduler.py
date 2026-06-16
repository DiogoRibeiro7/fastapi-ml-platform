import asyncio
from pathlib import Path

from app.core.scheduler import PeriodicScheduler
from app.db.session import build_session_factory, create_database_tables, dispose_engine
from app.repositories.drift_report_repository import DriftReportRepository
from app.services.drift_report_service import run_scheduled_drift_report


async def test_scheduler_runs_task_immediately_then_stops() -> None:
    """The scheduler should run the task once on start and stop cleanly."""

    runs = 0
    ran = asyncio.Event()

    async def task() -> None:
        nonlocal runs
        runs += 1
        ran.set()

    # A long interval means only the immediate run happens during the test.
    scheduler = PeriodicScheduler(3_600, task)
    scheduler.start()
    try:
        await asyncio.wait_for(ran.wait(), timeout=2.0)
    finally:
        await scheduler.stop()

    assert runs == 1


async def test_scheduler_keeps_running_after_task_error() -> None:
    """A failing task should be retried on the next tick, not crash the loop."""

    calls = 0
    second_call = asyncio.Event()

    async def task() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")
        second_call.set()

    scheduler = PeriodicScheduler(0.01, task)
    scheduler.start()
    try:
        await asyncio.wait_for(second_call.wait(), timeout=2.0)
    finally:
        await scheduler.stop()

    assert calls >= 2


async def test_scheduled_drift_report_is_stored(tmp_path: Path) -> None:
    """The scheduled task should compute and persist a drift report."""

    engine, session_factory = build_session_factory(
        f"sqlite+aiosqlite:///{tmp_path / 'sched.db'}"
    )
    await create_database_tables(engine)
    try:
        report_id = await run_scheduled_drift_report(session_factory)
        async with session_factory() as session:
            row = await DriftReportRepository(session).get_by_id(report_id)
        assert row is not None
        assert row.max_severity in {"none", "low", "medium", "high"}
    finally:
        await dispose_engine(engine)
