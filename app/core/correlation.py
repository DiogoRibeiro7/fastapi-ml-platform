import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar, Token

from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the correlation id for the current context, or '-' if unset."""

    return _request_id.get()


def set_request_id(value: str) -> Token[str]:
    """Set the correlation id for the current context."""

    return _request_id.set(value)


def reset_request_id(token: Token[str]) -> None:
    """Restore the previous correlation id."""

    _request_id.reset(token)


def generate_request_id() -> str:
    """Generate a new correlation id."""

    return uuid.uuid4().hex


async def correlation_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach a correlation id to the request context and response.

    An inbound X-Request-ID header is honored so a trace id can flow across
    services; otherwise a new id is generated. The id is exposed to logging
    through a context variable and echoed back in the response header.
    """

    request_id = request.headers.get(REQUEST_ID_HEADER) or generate_request_id()
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
    finally:
        reset_request_id(token)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
