from app.ml.model_loader import ModelBundle
from app.schemas.model import ModelMetadataResponse


class ModelService:
    """Business logic for model metadata."""

    def __init__(self, model_bundle: ModelBundle) -> None:
        self._model_bundle = model_bundle

    def current_model(self) -> ModelMetadataResponse:
        """Return active model metadata."""

        return ModelMetadataResponse(
            name=self._model_bundle.name,
            version=self._model_bundle.version,
            model_type=self._model_bundle.model_type,
            features=self._model_bundle.features,
            metrics=self._model_bundle.metrics,
            loaded_from=self._model_bundle.loaded_from,
            loaded_at=self._model_bundle.loaded_at,
        )
