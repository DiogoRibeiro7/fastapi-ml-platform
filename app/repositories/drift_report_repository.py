from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DriftReport


class DriftReportRepository:
    """Persistence operations for stored drift reports."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        report_id: str,
        sample_size: int,
        max_severity: str,
        summary: str,
        features: list[dict[str, Any]],
    ) -> DriftReport:
        """Persist a computed drift report."""

        row = DriftReport(
            id=report_id,
            sample_size=sample_size,
            max_severity=max_severity,
            summary=summary,
            features=features,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row

    async def get_by_id(self, report_id: str) -> DriftReport | None:
        """Fetch a drift report by id."""

        result = await self._session.execute(
            select(DriftReport).where(DriftReport.id == report_id)
        )
        return result.scalar_one_or_none()

    async def get_latest(self) -> DriftReport | None:
        """Return the most recently generated drift report."""

        result = await self._session.execute(
            select(DriftReport).order_by(desc(DriftReport.generated_at), desc(DriftReport.id))
        )
        return result.scalars().first()
