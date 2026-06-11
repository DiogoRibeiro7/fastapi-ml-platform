from app.ml.model_loader import ModelBundle


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

    @property
    def bundle(self) -> ModelBundle:
        """Return the currently served model bundle."""

        return self._bundle

    def swap(self, bundle: ModelBundle) -> None:
        """Replace the served model bundle."""

        self._bundle = bundle
