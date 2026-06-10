from app.repositories.prediction_repository import PredictionRepository
from app.schemas.metrics import ModelMetricsResponse


class MetricsService:
    """Business logic for operational model metrics."""

    def __init__(self, repository: PredictionRepository) -> None:
        self._repository = repository

    async def model_metrics(self) -> ModelMetricsResponse:
        """Return model metrics computed from stored prediction logs."""

        raw_metrics = await self._repository.aggregate_metrics()
        return ModelMetricsResponse(**raw_metrics)
