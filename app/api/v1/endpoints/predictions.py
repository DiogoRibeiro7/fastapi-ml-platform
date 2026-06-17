from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_prediction_service, require_roles
from app.core.exceptions import PredictionNotFoundError
from app.core.principal import PREDICT_ROLES
from app.schemas.prediction import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    PredictionResponse,
    TransactionInput,
)
from app.services.prediction_service import PredictionService

router = APIRouter(dependencies=[Depends(require_roles(*PREDICT_ROLES))])


@router.post(
    "/transactions/score",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def score_transaction(
    transaction: TransactionInput,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    """Score a single transaction for fraud risk."""

    return await service.score_transaction(transaction)


@router.post(
    "/transactions/batch-score",
    response_model=BatchPredictionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def score_batch(
    request: BatchPredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
) -> BatchPredictionResponse:
    """Score a batch of transactions for fraud risk."""

    try:
        return await service.score_batch(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc


@router.get(
    "/transactions/{transaction_id}",
    response_model=PredictionResponse,
)
async def get_prediction(
    transaction_id: str,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    """Fetch a stored prediction by transaction id."""

    try:
        return await service.get_prediction(transaction_id)
    except PredictionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
