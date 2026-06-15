class PredictionNotFoundError(LookupError):
    """Raised when a stored prediction cannot be found."""


class ModelUnavailableError(RuntimeError):
    """Raised when the scoring model cannot be used."""


class ModelNotFoundError(LookupError):
    """Raised when a registered model cannot be found."""


class DuplicateModelError(ValueError):
    """Raised when a model name and version pair is already registered."""


class ModelPromotionError(RuntimeError):
    """Raised when a registered model cannot be promoted to active."""


class JobNotFoundError(LookupError):
    """Raised when a batch job cannot be found."""


class DriftReportNotFoundError(LookupError):
    """Raised when a drift report cannot be found."""
