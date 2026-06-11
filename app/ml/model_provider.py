from app.ml.model_loader import ModelBundle
from app.ml.shap_explainer import ShapExplainer, build_shap_explainer


class ModelProvider:
    """Holds the live model bundle and supports hot-swapping it.

    The active model can change at runtime through the promotion workflow. A
    single provider instance lives on the application state, so every request
    reads the current bundle through it and a promotion is visible immediately.

    Attribute reassignment is atomic in CPython, which is sufficient for this
    single-process service. A multi-process deployment would coordinate
    promotions through shared state instead.
    """

    def __init__(self, bundle: ModelBundle) -> None:
        self._bundle = bundle
        self._shap_explainer: ShapExplainer | None = None

    @property
    def bundle(self) -> ModelBundle:
        """Return the currently served model bundle."""

        return self._bundle

    def swap(self, bundle: ModelBundle) -> None:
        """Replace the served model bundle and drop its cached explainer."""

        self._bundle = bundle
        self._shap_explainer = None

    def shap_explainer(self) -> ShapExplainer:
        """Return the SHAP explainer for the current model, building it once.

        The explainer is cached for the lifetime of the current model and
        rebuilt after a promotion swaps in a new model.
        """

        if self._shap_explainer is None:
            self._shap_explainer = build_shap_explainer(self._bundle)
        return self._shap_explainer
