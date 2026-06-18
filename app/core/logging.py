import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from app.core.correlation import get_request_id

# Field names that may carry personally identifiable or secret data and must
# never appear in plaintext in logs.
SENSITIVE_FIELDS = frozenset(
    {
        "customer_id",
        "email",
        "phone",
        "password",
        "card_number",
        "ssn",
        "api_key",
        "authorization",
        "token",
        "access_token",
    }
)
MASK = "***"

# LogRecord attributes that are part of the logging machinery, not user extras.
_RESERVED_ATTRS = frozenset(vars(logging.makeLogRecord({})))


class RequestIdFilter(logging.Filter):
    """Inject the current correlation id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class RedactingFilter(logging.Filter):
    """Mask sensitive fields on log records before they are emitted.

    Any extra attribute whose name is in the sensitive set is replaced with a
    mask, so PII or secrets passed via ``extra=`` never reach the log sink.
    """

    def __init__(self, sensitive_fields: frozenset[str] = SENSITIVE_FIELDS) -> None:
        super().__init__()
        self._sensitive = sensitive_fields

    def filter(self, record: logging.LogRecord) -> bool:
        for key in self._sensitive:
            if key in record.__dict__ and key not in _RESERVED_ATTRS:
                record.__dict__[key] = MASK
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure process-wide structured JSON logging with correlation ids."""

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.addFilter(RedactingFilter())
    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s"
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
