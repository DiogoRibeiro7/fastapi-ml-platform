from pathlib import Path

from app.core.exceptions import ModelNotFoundError, ModelPromotionError
from app.ml.model_loader import load_registered_bundle
from app.ml.model_provider import ModelProvider
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.schemas.model import (
    ModelRegistrationRequest,
    RegisteredModelListResponse,
    RegisteredModelResponse,
)


class ModelRegistryService:
    """Business logic for the model registry."""

    def __init__(
        self,
        repository: ModelRegistryRepository,
        model_provider: ModelProvider,
    ) -> None:
        self._repository = repository
        self._model_provider = model_provider

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
        """Promote one model to active and hot-swap the served model.

        The artifact is loaded before the database is updated, so a missing or
        invalid artifact aborts the promotion and leaves the current model and
        active flag untouched.
        """

        row = await self._repository.get_by_id(model_id)
        if row is None:
            raise ModelNotFoundError(f"Registered model not found: {model_id}")

        try:
            bundle = load_registered_bundle(
                artifact_path=Path(row.artifact_path),
                name=row.name,
                version=row.version,
                metrics=row.metrics,
            )
        except (FileNotFoundError, TypeError) as exc:
            raise ModelPromotionError(
                f"Cannot promote model {row.name} {row.version}: {exc}"
            ) from exc

        activated = await self._repository.activate(model_id)
        if activated is None:
            raise ModelNotFoundError(f"Registered model not found: {model_id}")

        self._model_provider.swap(bundle)
        return RegisteredModelResponse.model_validate(activated)
