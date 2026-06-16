import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import DriftReportNotFoundError
from app.core.jobs import JobQueue
from app.repositories.drift_report_repository import DriftReportRepository
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.drift import DriftJobResponse, StoredDriftReportResponse
from app.services.drift_service import DriftService

logger = logging.getLogger(__name__)


async def _compute_drift_report(
    report_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Compute a drift report in its own session and persist it."""

    async with session_factory() as session:
        drift = DriftService(PredictionRepository(session))
        report = await drift.current_report()
        await DriftReportRepository(session).create(
            report_id=report_id,
            sample_size=report.sample_size,
            max_severity=report.max_severity,
            summary=report.summary,
            features=[item.model_dump() for item in report.features],
        )
    logger.info("Drift report %s computed (severity=%s).", report_id, report.max_severity)


async def run_scheduled_drift_report(
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    """Compute and store a drift report; used by the periodic scheduler."""

    report_id = uuid4().hex
    await _compute_drift_report(report_id, session_factory)
    return report_id


class DriftReportService:
    """Schedules drift computation in the background and serves stored reports."""

    def __init__(
        self,
        *,
        repository: DriftReportRepository,
        session_factory: async_sessionmaker[AsyncSession],
        queue: JobQueue,
    ) -> None:
        self._repository = repository
        self._session_factory = session_factory
        self._queue = queue

    async def submit(self) -> DriftJobResponse:
        """Schedule a drift-computation job and return its report id."""

        report_id = uuid4().hex
        session_factory = self._session_factory

        async def run() -> None:
            await _compute_drift_report(report_id, session_factory)

        await self._queue.enqueue(run)
        return DriftJobResponse(report_id=report_id)

    async def get_report(self, report_id: str) -> StoredDriftReportResponse:
        """Return a stored drift report by id."""

        row = await self._repository.get_by_id(report_id)
        if row is None:
            raise DriftReportNotFoundError(f"Drift report not found: {report_id}")
        return StoredDriftReportResponse.model_validate(row)

    async def get_latest(self) -> StoredDriftReportResponse:
        """Return the most recent stored drift report."""

        row = await self._repository.get_latest()
        if row is None:
            raise DriftReportNotFoundError("No drift reports have been generated yet.")
        return StoredDriftReportResponse.model_validate(row)
