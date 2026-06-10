from fastapi import APIRouter, Depends

from app.api.dependencies import get_drift_service, require_api_key
from app.schemas.drift import DriftReportResponse
from app.services.drift_service import DriftService

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/drift/report", response_model=DriftReportResponse)
async def get_drift_report(
    service: DriftService = Depends(get_drift_service),
) -> DriftReportResponse:
    """Return a PSI-based drift report for recent predictions."""

    return await service.current_report()
