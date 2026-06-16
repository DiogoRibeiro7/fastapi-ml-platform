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


class DeadLetterNotFoundError(LookupError):
    """Raised when there are no dead-lettered transactions to act on."""


class IngestionError(ValueError):
    """Raised when an ingestion payload cannot be parsed or validated."""


class IngestionTooLargeError(ValueError):
    """Raised when an ingestion payload exceeds the allowed record count."""
