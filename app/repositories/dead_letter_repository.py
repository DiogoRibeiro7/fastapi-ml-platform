from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DeadLetter


class DeadLetterRepository:
    """Persistence operations for dead-lettered batch transactions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        job_id: str,
        transaction_id: str,
        payload: dict[str, Any],
        error: str,
    ) -> DeadLetter:
        """Record a failed transaction for a job."""

        row = DeadLetter(
            job_id=job_id,
            transaction_id=transaction_id,
            payload=payload,
            error=error,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def list_for_job(self, job_id: str) -> list[DeadLetter]:
        """Return all dead-lettered transactions for a job, oldest first."""

        result = await self._session.execute(
            select(DeadLetter).where(DeadLetter.job_id == job_id).order_by(DeadLetter.id)
        )
        return list(result.scalars().all())
