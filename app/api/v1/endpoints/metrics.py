from fastapi import APIRouter, Depends

from app.api.dependencies import get_metrics_service, require_roles
from app.core.principal import ALL_ROLES
from app.schemas.metrics import ModelMetricsResponse
from app.services.metrics_service import MetricsService

router = APIRouter(dependencies=[Depends(require_roles(*ALL_ROLES))])


@router.get("/metrics/model", response_model=ModelMetricsResponse)
async def get_model_metrics(
    service: MetricsService = Depends(get_metrics_service),
) -> ModelMetricsResponse:
    """Return operational metrics computed from prediction logs."""

    return await service.model_metrics()
