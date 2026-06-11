from app.core.exceptions import ModelNotFoundError
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.schemas.model import (
    ModelRegistrationRequest,
    RegisteredModelListResponse,
    RegisteredModelResponse,
)


class ModelRegistryService:
    """Business logic for the model registry."""

    def __init__(self, repository: ModelRegistryRepository) -> None:
        self._repository = repository

    async def register_model(
        self, request: ModelRegistrationRequest
    ) -> RegisteredModelResponse:
        """Register a new model version. New models start inactive."""

        row = await self._repository.create(
            name=request.name,
            version=request.version,
            artifact_path=request.artifact_path,
            training_dataset=request.training_dataset,
            metrics=request.metrics,
        )
        return RegisteredModelResponse.model_validate(row)

    async def list_models(self) -> RegisteredModelListResponse:
        """Return all registered models, newest first."""

        rows = await self._repository.list_all()
        return RegisteredModelListResponse(
            models=[RegisteredModelResponse.model_validate(row) for row in rows]
        )

    async def activate_model(self, model_id: int) -> RegisteredModelResponse:
        """Activate one model; all other models become inactive."""

        row = await self._repository.activate(model_id)
        if row is None:
            raise ModelNotFoundError(f"Registered model not found: {model_id}")
        return RegisteredModelResponse.model_validate(row)
