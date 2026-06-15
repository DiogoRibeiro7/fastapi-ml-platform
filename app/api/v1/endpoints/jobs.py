from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_batch_job_service, require_api_key
from app.core.exceptions import JobNotFoundError
from app.schemas.jobs import BatchJobResponse
from app.schemas.prediction import BatchPredictionRequest
from app.services.batch_job_service import BatchJobService

router = APIRouter(dependencies=[Depends(require_api_key)])


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
