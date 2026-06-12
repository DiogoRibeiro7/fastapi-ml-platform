import time
from collections.abc import Awaitable, Callable

from prometheus_client import Counter, Histogram
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests.",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
)
PREDICTION_LATENCY = Histogram(
    "model_prediction_duration_seconds",
    "Model inference latency in seconds, separate from HTTP latency.",
)
PREDICTION_COUNT = Counter(
    "model_predictions_total",
    "Scored predictions by risk level and decision.",
    ["risk_level", "decision"],
)


def record_prediction(risk_level: str, decision: str, duration_seconds: float) -> None:
    """Record one scored prediction's latency and risk/decision labels."""

    PREDICTION_LATENCY.observe(duration_seconds)
    PREDICTION_COUNT.labels(risk_level=risk_level, decision=decision).inc()


async def prometheus_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Record request count and latency by method, route, and status code.

    Instrumentation lives here rather than in route handlers. The matched route
    template is used as the endpoint label to avoid unbounded label cardinality
    from path parameters; unmatched paths are bucketed under "unmatched".
    """

    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    route = request.scope.get("route")
    endpoint = getattr(route, "path", None) or "unmatched"
    REQUEST_COUNT.labels(request.method, endpoint, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)
    return response
