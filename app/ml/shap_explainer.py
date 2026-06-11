import logging

import numpy as np
from numpy.typing import NDArray

from app.ml.model_loader import ModelBundle, ProbabilityModel

logger = logging.getLogger(__name__)


class ShapExplainer:
    """Lazily-built SHAP explainer for a fraud probability model.

    The underlying SHAP explainer is expensive to construct, so it is built on
    the first explanation and cached. Any failure (SHAP not installed, an
    incompatible model) is logged once and disables the explainer so callers
    fall back to the linear explanation without repeated errors.
    """

    def __init__(
        self,
        model: ProbabilityModel,
        feature_names: list[str],
        background: NDArray[np.float64],
    ) -> None:
        self._model = model
        self._feature_names = feature_names
        self._background = background
        self._explainer: object | None = None
        self._unavailable = False

    def _build_explainer(self) -> object:
        """Construct a SHAP explainer over the positive-class probability."""

        import shap

        def positive_class_probability(data: NDArray[np.float64]) -> NDArray[np.float64]:
            return np.asarray(self._model.predict_proba(data))[:, 1]

        return shap.Explainer(positive_class_probability, self._background)

    def explain(self, feature_array: NDArray[np.float64]) -> dict[str, float] | None:
        """Return per-feature SHAP values for one row, or None on failure."""

        if self._unavailable:
            return None

        try:
            if self._explainer is None:
                self._explainer = self._build_explainer()
            explanation = self._explainer(feature_array)  # type: ignore[operator]
            values = np.asarray(explanation.values)[0]
            return {
                name: float(value)
                for name, value in zip(self._feature_names, values, strict=True)
            }
        except Exception:
            logger.exception("SHAP explanation failed; falling back to linear contributions.")
            self._unavailable = True
            return None


def build_shap_explainer(bundle: ModelBundle, background_size: int = 100) -> ShapExplainer:
    """Build a SHAP explainer for a model bundle using a synthetic background."""

    from app.ml.training import make_synthetic_dataset

    features, _ = make_synthetic_dataset(n_samples=background_size, seed=7)
    return ShapExplainer(
        model=bundle.model,
        feature_names=bundle.features,
        background=features,
    )
