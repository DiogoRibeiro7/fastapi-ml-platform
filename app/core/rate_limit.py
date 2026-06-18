import hashlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Infrastructure endpoints are never rate limited.
EXCLUDED_PATHS = frozenset({"/health", "/ready", "/metrics"})


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a rate-limit check."""

    allowed: bool
    retry_after: int
    remaining: int


class RateLimiter:
    """Fixed-window, per-client request counter.

    State is in-process, which suits a single instance. A distributed
    deployment would back this with a shared store such as Redis.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._clock = clock
        self._state: dict[str, tuple[float, int]] = {}

    def check(self, key: str) -> RateLimitResult:
        """Record a request for a client and report whether it is allowed."""

        now = self._clock()
        start, count = self._state.get(key, (now, 0))
        if now - start >= self._window:
            start, count = now, 0

        count += 1
        self._state[key] = (start, count)

        if count > self._max:
            retry_after = int(self._window - (now - start)) + 1
            return RateLimitResult(allowed=False, retry_after=retry_after, remaining=0)
        return RateLimitResult(
            allowed=True, retry_after=0, remaining=max(self._max - count, 0)
        )


def client_key(request: Request) -> str:
    """Derive a stable per-client key from credentials or the client address.

    Credentials are hashed so raw secrets are never used as map keys.
    """

    api_key = request.headers.get("X-API-Key")
    if api_key:
        return "key:" + hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]

    authorization = request.headers.get("Authorization")
    if authorization:
        return "tok:" + hashlib.sha256(authorization.encode("utf-8")).hexdigest()[:16]

    host = request.client.host if request.client else "unknown"
    return f"ip:{host}"


def make_rate_limit_middleware(
    limiter: RateLimiter,
    excluded_paths: frozenset[str] = EXCLUDED_PATHS,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Build a middleware that enforces per-client rate limits."""

    async def middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in excluded_paths:
            return await call_next(request)

        result = limiter.check(client_key(request))
        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded."},
                headers={"Retry-After": str(result.retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response

    return middleware
