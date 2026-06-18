from typing import Any

from app.core.config import Settings
from app.schemas.prediction import TransactionInput
from app.services.batch_tasks import run_batch_job_task


def make_rq_queue(redis_url: str) -> Any:  # noqa: ANN401 - rq.Queue is untyped and optional
    """Build an RQ queue connected to Redis.

    Imported lazily so redis/rq are only required when the redis job backend is
    selected.
    """

    from redis import Redis
    from rq import Queue

    return Queue(connection=Redis.from_url(redis_url))


class RedisBatchDispatcher:
    """Dispatch batch jobs to an RQ queue for a separate worker to execute."""

    def __init__(self, rq_queue: Any, settings: Settings) -> None:  # noqa: ANN401
        self._queue = rq_queue
        self._settings = settings

    async def dispatch(self, job_id: str, transactions: list[TransactionInput]) -> None:
        """Enqueue the job as a serializable RQ task."""

        payload = [transaction.model_dump(mode="json") for transaction in transactions]
        self._queue.enqueue(run_batch_job_task, job_id, payload, self._settings)
