from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import DeadLetter, DriftReport, PredictionLog


class RetentionService:
    """Delete records older than the configured retention window."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def purge(self, retention_days: int) -> dict[str, int]:
        """Delete prediction logs, drift reports, and dead letters past the window.

        Returns the number of rows deleted per table.
        """

        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        targets = [
            ("prediction_logs", PredictionLog, PredictionLog.created_at),
            ("drift_reports", DriftReport, DriftReport.generated_at),
            ("dead_letters", DeadLetter, DeadLetter.created_at),
        ]

        deleted: dict[str, int] = {}
        for name, model, timestamp_column in targets:
            result = await self._session.execute(
                delete(model).where(timestamp_column < cutoff)
            )
            # execute() is typed as Result, but a DELETE yields a CursorResult.
            deleted[name] = int(getattr(result, "rowcount", 0) or 0)

        await self._session.commit()
        return deleted


async def run_retention_cleanup(
    session_factory: async_sessionmaker[AsyncSession],
    retention_days: int,
) -> dict[str, int]:
    """Run a retention purge in its own session; used by the scheduler."""

    async with session_factory() as session:
        return await RetentionService(session).purge(retention_days)
