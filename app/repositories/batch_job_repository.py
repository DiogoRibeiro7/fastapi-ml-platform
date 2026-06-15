from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BatchJob, utc_now


class BatchJobRepository:
    """Persistence operations for batch-scoring jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, job_id: str, total: int) -> BatchJob:
        """Create a queued job row."""

        row = BatchJob(id=job_id, status="queued", total=total, completed=0)
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def get(self, job_id: str) -> BatchJob | None:
        """Fetch a job by id."""

        result = await self._session.execute(select(BatchJob).where(BatchJob.id == job_id))
        return result.scalar_one_or_none()

    async def mark_running(self, job_id: str) -> None:
        """Mark a job as running and stamp its start time."""

        row = await self.get(job_id)
        if row is None:
            return
        row.status = "running"
        row.started_at = utc_now()
        await self._session.commit()

    async def update_progress(self, job_id: str, completed: int) -> None:
        """Update the completed-transaction count for a job."""

        row = await self.get(job_id)
        if row is None:
            return
        row.completed = completed
        await self._session.commit()

    async def mark_completed(self, job_id: str, result: dict[str, Any]) -> None:
        """Mark a job completed with a result summary."""

        row = await self.get(job_id)
        if row is None:
            return
        row.status = "completed"
        row.result = result
        row.finished_at = utc_now()
        await self._session.commit()

    async def mark_failed(self, job_id: str, error: str) -> None:
        """Mark a job failed with an error message."""

        row = await self.get(job_id)
        if row is None:
            return
        row.status = "failed"
        row.error = error
        row.finished_at = utc_now()
        await self._session.commit()
