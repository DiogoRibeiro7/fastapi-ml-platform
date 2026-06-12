import logging

from fastapi.testclient import TestClient

from app.core.correlation import (
    generate_request_id,
    get_request_id,
    reset_request_id,
    set_request_id,
)
from app.core.logging import RequestIdFilter


def test_response_includes_generated_request_id(client: TestClient) -> None:
    """A request without a correlation id should receive a generated one."""

    response = client.get("/health")

    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32  # uuid4 hex


def test_inbound_request_id_is_echoed(client: TestClient) -> None:
    """A provided correlation id should be propagated to the response."""

    response = client.get("/health", headers={"X-Request-ID": "trace-123"})

    assert response.headers["X-Request-ID"] == "trace-123"


def test_request_id_context_default_and_set() -> None:
    """The correlation context variable defaults to '-' and is settable."""

    assert get_request_id() == "-"
    token = set_request_id("abc")
    try:
        assert get_request_id() == "abc"
    finally:
        reset_request_id(token)
    assert get_request_id() == "-"


def test_request_id_filter_injects_id_into_log_record() -> None:
    """The logging filter should stamp the active correlation id on records."""

    token = set_request_id("log-id")
    try:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__, lineno=1,
            msg="hello", args=(), exc_info=None,
        )
        assert RequestIdFilter().filter(record) is True
        assert record.request_id == "log-id"
    finally:
        reset_request_id(token)


def test_generated_ids_are_unique() -> None:
    """Generated correlation ids should not collide."""

    assert generate_request_id() != generate_request_id()
