from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_evaluation_service, require_api_key
from app.schemas.evaluation import EvaluationReportResponse
from app.services.evaluation_service import EvaluationService

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/evaluation/report", response_model=EvaluationReportResponse)
async def get_evaluation_report(
    threshold: float | None = Query(default=None, ge=0.0, le=1.0),
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationReportResponse:
    """Return a consolidated offline evaluation report for the active model.

    The decision threshold defaults to the configured decline score.
    """

    return service.current_report(threshold=threshold)
