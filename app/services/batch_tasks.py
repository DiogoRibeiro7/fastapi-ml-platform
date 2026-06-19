import asyncio
from typing import Any

from app.core.config import Settings
from app.core.correlation import reset_request_id, set_request_id
from app.db.session import build_session_factory, dispose_engine
from app.ml.model_loader import load_model_bundle
from app.schemas.prediction import TransactionInput
from app.services.batch_job_service import _process_job


async def _run_batch_job(
    job_id: str,
    transactions_data: list[dict[str, Any]],
    settings: Settings,
) -> None:
    """Rebuild dependencies from settings and score a job's transactions.

    Runs in an RQ worker process that shares no state with the API, so it
    constructs its own database session factory and loads the model from the
    configured artifact.
    """

    engine, session_factory = build_session_factory(settings.database_url)
    try:
        bundle = load_model_bundle(
            artifact_path=settings.model_artifact_path,
            metadata_path=settings.model_metadata_path,
            train_if_missing=False,
        )
        transactions = [TransactionInput.model_validate(item) for item in transactions_data]
        await _process_job(job_id, transactions, session_factory, bundle, settings)
    finally:
        await dispose_engine(engine)


def run_batch_job_task(
    job_id: str,
    transactions_data: list[dict[str, Any]],
    settings: Settings,
    request_id: str = "-",
) -> None:
    """RQ entrypoint: run the async job, carrying the originating request id.

    The correlation id is restored from the enqueued job so the worker's log
    lines tie back to the request that submitted the batch, even though the
    worker runs in a separate process.
    """

    token = set_request_id(request_id)
    try:
        asyncio.run(_run_batch_job(job_id, transactions_data, settings))
    finally:
        reset_request_id(token)
