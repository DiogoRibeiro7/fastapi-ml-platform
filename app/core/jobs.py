import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

logger = logging.getLogger(__name__)

JobCallable = Callable[[], Awaitable[None]]


class JobQueue(Protocol):
    """Schedules background jobs for execution."""

    async def enqueue(self, job: JobCallable) -> None:
        """Schedule a job for execution."""
        ...


class InlineJobQueue:
    """Run jobs synchronously, awaiting completion before returning.

    Used in tests so job processing is deterministic. A Redis/RQ-backed queue
    can implement the same interface for distributed processing.
    """

    async def enqueue(self, job: JobCallable) -> None:
        """Run the job to completion."""

        await job()


class BackgroundJobQueue:
    """Run jobs as fire-and-forget asyncio tasks on the running event loop.

    A strong reference to each task is held until it finishes so it is not
    garbage collected mid-flight.
    """

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    async def enqueue(self, job: JobCallable) -> None:
        """Schedule the job without awaiting its result."""

        task = asyncio.create_task(self._run(job))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @staticmethod
    async def _run(job: JobCallable) -> None:
        try:
            await job()
        except Exception:
            logger.exception("Background job failed.")
