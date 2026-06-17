from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_batch_job_service,
    get_ingestion_service,
    require_roles,
)
from app.core.exceptions import (
    DeadLetterNotFoundError,
    IngestionError,
    IngestionTooLargeError,
    JobNotFoundError,
)
from app.core.principal import PREDICT_ROLES
from app.schemas.jobs import BatchJobResponse, DeadLetterListResponse
from app.schemas.prediction import BatchPredictionRequest
from app.services.batch_job_service import BatchJobService
from app.services.ingestion_service import IngestionService

router = APIRouter(dependencies=[Depends(require_roles(*PREDICT_ROLES))])


@router.post(
    "/transactions/batch-score-jobs",
    response_model=BatchJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_batch_job(
    request: BatchPredictionRequest,
    service: BatchJobService = Depends(get_batch_job_service),
) -> BatchJobResponse:
    """Submit a batch of transactions for asynchronous scoring."""

    return await service.submit(request)


@router.post(
    "/transactions/ingest",
    response_model=BatchJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_transactions(
    request: Request,
    service: IngestionService = Depends(get_ingestion_service),
) -> BatchJobResponse:
    """Ingest a payload of transactions (JSON array or newline-delimited JSON).

    The payload is parsed and submitted as an asynchronous batch-scoring job.
    """

    raw = await request.body()
    try:
        return await service.ingest(raw)
    except IngestionTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except IngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/jobs/{job_id}", response_model=BatchJobResponse)
async def get_job(
    job_id: str,
    service: BatchJobService = Depends(get_batch_job_service),
) -> BatchJobResponse:
    """Return the status and result of a batch-scoring job."""

    try:
        return await service.get_job(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/jobs/{job_id}/dead-letters", response_model=DeadLetterListResponse)
async def get_job_dead_letters(
    job_id: str,
    service: BatchJobService = Depends(get_batch_job_service),
) -> DeadLetterListResponse:
    """List the transactions that failed scoring within a job."""

    try:
        return await service.list_dead_letters(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/jobs/{job_id}/retry-dead-letters",
    response_model=BatchJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_job_dead_letters(
    job_id: str,
    service: BatchJobService = Depends(get_batch_job_service),
) -> BatchJobResponse:
    """Resubmit a job's dead-lettered transactions as a new batch job."""

    try:
        return await service.retry_dead_letters(job_id)
    except DeadLetterNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
