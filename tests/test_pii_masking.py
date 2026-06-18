import logging

import pytest

from app.core.logging import MASK, RedactingFilter, configure_logging


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord("test", logging.INFO, "x.py", 1, "event", (), None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_redacting_filter_masks_sensitive_fields() -> None:
    """Sensitive extras should be masked; non-sensitive ones left intact."""

    record = _record(customer_id="cust_123", email="a@b.com", amount=100.0)

    assert RedactingFilter().filter(record) is True
    assert record.customer_id == MASK
    assert record.email == MASK
    assert record.amount == 100.0


def test_redacting_filter_ignores_reserved_attributes() -> None:
    """The filter must not clobber core LogRecord attributes."""

    record = _record()

    RedactingFilter().filter(record)

    assert record.levelname == "INFO"
    assert record.getMessage() == "event"


def test_configure_logging_installs_redacting_filter() -> None:
    """configure_logging should attach a redacting filter to the handler."""

    configure_logging("INFO")
    try:
        handler = logging.getLogger().handlers[0]
        assert any(isinstance(f, RedactingFilter) for f in handler.filters)
    finally:
        logging.getLogger().handlers.clear()


def test_pii_is_masked_in_emitted_logs(capsys: pytest.CaptureFixture[str]) -> None:
    """A sensitive field passed via extra must not appear in plaintext output."""

    configure_logging("INFO")
    try:
        logging.getLogger("test.pii").info(
            "prediction_created", extra={"customer_id": "cust_123", "amount": 100}
        )
        output = capsys.readouterr().out
    finally:
        logging.getLogger().handlers.clear()

    assert "cust_123" not in output
    assert MASK in output
    assert "100" in output  # non-sensitive field is preserved
