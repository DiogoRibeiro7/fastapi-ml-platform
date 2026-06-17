from fastapi import APIRouter, Depends

from app.api.dependencies import get_threshold_service, require_roles
from app.core.principal import ALL_ROLES
from app.schemas.threshold import (
    ThresholdOptimizationRequest,
    ThresholdOptimizationResponse,
)
from app.services.threshold_service import ThresholdOptimizationService

router = APIRouter(dependencies=[Depends(require_roles(*ALL_ROLES))])


@router.post("/threshold/optimize", response_model=ThresholdOptimizationResponse)
async def optimize_threshold(
    request: ThresholdOptimizationRequest,
    service: ThresholdOptimizationService = Depends(get_threshold_service),
) -> ThresholdOptimizationResponse:
    """Recommend a cost-minimizing decision threshold for the active model."""

    return service.optimize(request)
