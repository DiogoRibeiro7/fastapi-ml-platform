import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.core.config import Settings

logger = logging.getLogger(__name__)

# Set once tracing is configured. Kept module-level so the hot path can create
# spans without importing OpenTelemetry when tracing is disabled.
_tracer: Any = None


def configure_tracing(app: "FastAPI", settings: "Settings") -> None:
    """Set up OpenTelemetry tracing and instrument the FastAPI app.

    OpenTelemetry is an optional dependency, so every import here is local. When
    an OTLP endpoint is configured spans are exported there; otherwise they go
    to the console, which keeps local runs self-contained.
    """

    global _tracer

    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        exporter: Any = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    _tracer = trace.get_tracer("app.fraud")
    logger.info("OpenTelemetry tracing enabled (service=%s).", settings.otel_service_name)


@contextmanager
def start_span(name: str) -> Iterator[None]:
    """Start a child span, or do nothing when tracing is disabled."""

    if _tracer is None:
        yield
        return

    with _tracer.start_as_current_span(name):
        yield
