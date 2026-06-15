import logging
from collections import Counter
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.exceptions import JobNotFoundError
from app.core.jobs import JobQueue
from app.ml.model_loader import ModelBundle
from app.repositories.batch_job_repository import BatchJobRepository
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.jobs import BatchJobResponse
from app.schemas.prediction import BatchPredictionRequest, TransactionInput
from app.services.prediction_service import PredictionService

logger = logging.getLogger(__name__)


async def _process_job(
    job_id: str,
    transactions: list[TransactionInput],
    session_factory: async_sessionmaker[AsyncSession],
    model_bundle: ModelBundle,
    settings: Settings,
) -> None:
    """Score every transaction in a job using a fresh database session.

    Runs outside the submitting request, so it owns its own session and never
    touches the request's session. Progress and the final summary are persisted
    as the job advances.
    """

    async with session_factory() as session:
        jobs = BatchJobRepository(session)
        predictions = PredictionService(
            repository=PredictionRepository(session),
            model_bundle=model_bundle,
            settings=settings,
        )
        await jobs.mark_running(job_id)

        risk_levels: Counter[str] = Counter()
        decisions: Counter[str] = Counter()
        try:
            for index, transaction in enumerate(transactions, start=1):
                response = await predictions.score_transaction(transaction)
                risk_levels[response.risk_level] += 1
                decisions[response.decision] += 1
                await jobs.update_progress(job_id, index)

            await jobs.mark_completed(
                job_id,
                {
                    "risk_level_counts": dict(risk_levels),
                    "decision_counts": dict(decisions),
                },
            )
        except Exception as exc:
            logger.exception("Batch job %s failed.", job_id)
            await jobs.mark_failed(job_id, str(exc))


class BatchJobService:
    """Business logic for asynchronous batch-scoring jobs."""

    def __init__(
        self,
        *,
        repository: BatchJobRepository,
        session_factory: async_sessionmaker[AsyncSession],
        model_bundle: ModelBundle,
        settings: Settings,
        queue: JobQueue,
    ) -> None:
        self._repository = repository
        self._session_factory = session_factory
        self._model_bundle = model_bundle
        self._settings = settings
        self._queue = queue

    async def submit(self, request: BatchPredictionRequest) -> BatchJobResponse:
        """Create a job and enqueue it for background scoring."""

        job_id = uuid4().hex
        row = await self._repository.create(job_id=job_id, total=len(request.transactions))

        transactions = list(request.transactions)
        model_bundle = self._model_bundle
        settings = self._settings
        session_factory = self._session_factory

        async def run() -> None:
            await _process_job(job_id, transactions, session_factory, model_bundle, settings)

        await self._queue.enqueue(run)
        return BatchJobResponse.model_validate(row)

    async def get_job(self, job_id: str) -> BatchJobResponse:
        """Return a job's status and result by id."""

        row = await self._repository.get(job_id)
        if row is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        return BatchJobResponse.model_validate(row)
