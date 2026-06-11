from fastapi import APIRouter, Depends

from app.api.dependencies import get_calibration_service, require_api_key
from app.schemas.calibration import CalibrationReportResponse
from app.services.calibration_service import CalibrationService

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/calibration/report", response_model=CalibrationReportResponse)
async def get_calibration_report(
    service: CalibrationService = Depends(get_calibration_service),
) -> CalibrationReportResponse:
    """Return a calibration report for the active model on a labeled holdout."""

    return service.current_report()
