from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_drift_report_service,
    get_drift_service,
    require_roles,
)
from app.core.exceptions import DriftReportNotFoundError
from app.core.principal import ALL_ROLES
from app.schemas.drift import (
    DriftJobResponse,
    DriftReportResponse,
    StoredDriftReportResponse,
)
from app.services.drift_report_service import DriftReportService
from app.services.drift_service import DriftService

router = APIRouter(dependencies=[Depends(require_roles(*ALL_ROLES))])


@router.get("/drift/report", response_model=DriftReportResponse)
async def get_drift_report(
    service: DriftService = Depends(get_drift_service),
) -> DriftReportResponse:
    """Return a PSI-based drift report computed on demand for recent predictions."""

    return await service.current_report()


@router.post(
    "/drift/jobs",
    response_model=DriftJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_drift_job(
    service: DriftReportService = Depends(get_drift_report_service),
) -> DriftJobResponse:
    """Schedule a background drift-computation job and store the result."""

    return await service.submit()


@router.get("/drift/reports/latest", response_model=StoredDriftReportResponse)
async def get_latest_drift_report(
    service: DriftReportService = Depends(get_drift_report_service),
) -> StoredDriftReportResponse:
    """Return the most recently stored drift report."""

    try:
        return await service.get_latest()
    except DriftReportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/drift/reports/{report_id}", response_model=StoredDriftReportResponse)
async def get_stored_drift_report(
    report_id: str,
    service: DriftReportService = Depends(get_drift_report_service),
) -> StoredDriftReportResponse:
    """Return a stored drift report by id."""

    try:
        return await service.get_report(report_id)
    except DriftReportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
