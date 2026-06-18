from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def make_request_size_limit_middleware(
    max_bytes: int,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Build middleware that rejects requests whose body exceeds max_bytes.

    The check uses the Content-Length header, so an oversized body is refused
    before it is read into memory. Requests without a length (rare here) pass
    through and are still bounded by downstream limits such as the ingestion cap.
    """

    async def middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                declared = -1
            if declared > max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body exceeds {max_bytes} bytes."},
                )
        return await call_next(request)

    return middleware
