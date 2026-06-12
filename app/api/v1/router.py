from fastapi import APIRouter

from app.api.v1.endpoints import (
    calibration,
    drift,
    evaluation,
    health,
    metrics,
    models,
    observability,
    predictions,
    threshold,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(observability.router)
api_router.include_router(predictions.router, prefix="/v1", tags=["predictions"])
api_router.include_router(models.router, prefix="/v1", tags=["models"])
api_router.include_router(metrics.router, prefix="/v1", tags=["metrics"])
api_router.include_router(drift.router, prefix="/v1", tags=["drift"])
api_router.include_router(calibration.router, prefix="/v1", tags=["calibration"])
api_router.include_router(threshold.router, prefix="/v1", tags=["threshold"])
api_router.include_router(evaluation.router, prefix="/v1", tags=["evaluation"])
