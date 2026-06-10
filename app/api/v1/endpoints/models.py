from fastapi import APIRouter, Depends

from app.api.dependencies import get_model_service, require_api_key
from app.schemas.model import ModelMetadataResponse
from app.services.model_service import ModelService

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/models/current", response_model=ModelMetadataResponse)
async def get_current_model(
    service: ModelService = Depends(get_model_service),
) -> ModelMetadataResponse:
    """Return metadata for the active model."""

    return service.current_model()
