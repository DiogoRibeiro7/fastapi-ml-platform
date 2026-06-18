import logging
from collections import Counter
from typing import Protocol
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.exceptions import DeadLetterNotFoundError, JobNotFoundError
from app.core.jobs import JobQueue
from app.ml.model_loader import ModelBundle
from app.repositories.batch_job_repository import BatchJobRepository
from app.repositories.dead_letter_repository import DeadLetterRepository
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.jobs import (
    BatchJobResponse,
    DeadLetterListResponse,
    DeadLetterResponse,
)
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
        dead_letters = DeadLetterRepository(session)
        predictions = PredictionService(
            repository=PredictionRepository(session),
            model_bundle=model_bundle,
            settings=settings,
        )
        await jobs.mark_running(job_id)

        risk_levels: Counter[str] = Counter()
        decisions: Counter[str] = Counter()
        failed = 0
        try:
            for index, transaction in enumerate(transactions, start=1):
                try:
                    response = await predictions.score_transaction(transaction)
                    risk_levels[response.risk_level] += 1
                    decisions[response.decision] += 1
                except Exception as exc:
                    # Isolate a single bad transaction: dead-letter it and keep going.
                    failed += 1
                    logger.warning(
                        "Dead-lettering transaction %s in job %s: %s",
                        transaction.resolved_transaction_id,
                        job_id,
                        exc,
                    )
                    await dead_letters.create(
                        job_id=job_id,
                        transaction_id=transaction.resolved_transaction_id,
                        payload=transaction.model_dump(mode="json"),
                        error=str(exc),
                    )
                await jobs.update_progress(job_id, index)

            await jobs.mark_completed(
                job_id,
                {
                    "scored": int(sum(decisions.values())),
                    "failed": failed,
                    "risk_level_counts": dict(risk_levels),
                    "decision_counts": dict(decisions),
                },
            )
        except Exception as exc:
            logger.exception("Batch job %s failed.", job_id)
            await jobs.mark_failed(job_id, str(exc))


class BatchJobDispatcher(Protocol):
    """Hands a created job off for execution by some backend."""

    async def dispatch(self, job_id: str, transactions: list[TransactionInput]) -> None:
        """Schedule scoring of a job's transactions."""
        ...


class InProcessBatchDispatcher:
    """Run batch jobs on the in-process async queue (closure-based)."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        model_bundle: ModelBundle,
        settings: Settings,
        queue: JobQueue,
    ) -> None:
        self._session_factory = session_factory
        self._model_bundle = model_bundle
        self._settings = settings
        self._queue = queue

    async def dispatch(self, job_id: str, transactions: list[TransactionInput]) -> None:
        """Enqueue the job as a closure over the live session factory and model."""

        async def run() -> None:
            await _process_job(
                job_id, transactions, self._session_factory, self._model_bundle, self._settings
            )

        await self._queue.enqueue(run)


class BatchJobService:
    """Business logic for asynchronous batch-scoring jobs."""

    def __init__(
        self,
        *,
        repository: BatchJobRepository,
        dead_letter_repository: DeadLetterRepository,
        dispatcher: BatchJobDispatcher,
    ) -> None:
        self._repository = repository
        self._dead_letter_repository = dead_letter_repository
        self._dispatcher = dispatcher

    async def submit(self, request: BatchPredictionRequest) -> BatchJobResponse:
        """Create a job and dispatch it for background scoring."""

        job_id = uuid4().hex
        row = await self._repository.create(job_id=job_id, total=len(request.transactions))
        await self._dispatcher.dispatch(job_id, list(request.transactions))
        return BatchJobResponse.model_validate(row)

    async def get_job(self, job_id: str) -> BatchJobResponse:
        """Return a job's status and result by id."""

        row = await self._repository.get(job_id)
        if row is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        return BatchJobResponse.model_validate(row)

    async def list_dead_letters(self, job_id: str) -> DeadLetterListResponse:
        """Return the dead-lettered transactions for a job."""

        if await self._repository.get(job_id) is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        rows = await self._dead_letter_repository.list_for_job(job_id)
        return DeadLetterListResponse(
            job_id=job_id,
            dead_letters=[DeadLetterResponse.model_validate(row) for row in rows],
        )

    async def retry_dead_letters(self, job_id: str) -> BatchJobResponse:
        """Resubmit a job's dead-lettered transactions as a new batch job."""

        rows = await self._dead_letter_repository.list_for_job(job_id)
        if not rows:
            raise DeadLetterNotFoundError(f"No dead letters to retry for job: {job_id}")

        transactions = [TransactionInput.model_validate(row.payload) for row in rows]
        return await self.submit(BatchPredictionRequest(transactions=transactions))
