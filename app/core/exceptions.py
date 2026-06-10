class PredictionNotFoundError(LookupError):
    """Raised when a stored prediction cannot be found."""


class ModelUnavailableError(RuntimeError):
    """Raised when the scoring model cannot be used."""
