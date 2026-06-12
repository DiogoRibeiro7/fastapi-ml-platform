import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from app.core.correlation import get_request_id


class RequestIdFilter(logging.Filter):
    """Inject the current correlation id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure process-wide structured JSON logging with correlation ids."""

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s"
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
