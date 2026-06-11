from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_model_registry_service, get_model_service, require_api_key
from app.core.exceptions import DuplicateModelError, ModelNotFoundError, ModelPromotionError
from app.schemas.model import (
    ModelComparisonResponse,
    ModelMetadataResponse,
    ModelRegistrationRequest,
    RegisteredModelListResponse,
    RegisteredModelResponse,
)
from app.services.model_registry_service import ModelRegistryService
from app.services.model_service import ModelService

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/models/current", response_model=ModelMetadataResponse)
async def get_current_model(
    service: ModelService = Depends(get_model_service),
) -> ModelMetadataResponse:
    """Return metadata for the active model."""

    return service.current_model()


@router.get("/models", response_model=RegisteredModelListResponse)
async def list_models(
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> RegisteredModelListResponse:
    """List all registered models, newest first."""

    return await service.list_models()


@router.get("/models/compare", response_model=ModelComparisonResponse)
async def compare_models(
    baseline_id: int,
    candidate_id: int,
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> ModelComparisonResponse:
    """Compare two registered model versions by their stored metrics."""

    try:
        return await service.compare_models(baseline_id, candidate_id)
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/models",
    response_model=RegisteredModelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_model(
    request: ModelRegistrationRequest,
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> RegisteredModelResponse:
    """Register a new model version. New models start inactive."""

    try:
        return await service.register_model(request)
    except DuplicateModelError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/models/{model_id}/activate", response_model=RegisteredModelResponse)
async def activate_model(
    model_id: int,
    service: ModelRegistryService = Depends(get_model_registry_service),
) -> RegisteredModelResponse:
    """Activate one registered model; any other active model is deactivated."""

    try:
        return await service.activate_model(model_id)
    except ModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ModelPromotionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
