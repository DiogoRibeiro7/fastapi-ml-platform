import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class PeriodicScheduler:
    """Run an async task repeatedly on a fixed interval.

    The task runs once immediately on start, then every ``interval_seconds``.
    A failing task is logged and does not stop the schedule. The scheduler is
    generic so any periodic report (drift, quality snapshots) can use it.
    """

    def __init__(
        self,
        interval_seconds: float,
        task: Callable[[], Awaitable[None]],
    ) -> None:
        self._interval = interval_seconds
        self._task = task
        self._handle: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start the scheduling loop if it is not already running."""

        if self._handle is None:
            self._handle = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Cancel the scheduling loop and wait for it to unwind."""

        if self._handle is None:
            return
        self._handle.cancel()
        try:
            await self._handle
        except asyncio.CancelledError:
            pass
        self._handle = None

    async def _run(self) -> None:
        while True:
            try:
                await self._task()
            except Exception:
                logger.exception("Scheduled task failed.")
            await asyncio.sleep(self._interval)
