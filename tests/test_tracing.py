import pytest

from app.core import tracing


def test_start_span_is_noop_when_tracing_disabled() -> None:
    """start_span should be a harmless no-op when tracing is not configured."""

    assert tracing._tracer is None
    with tracing.start_span("model.inference"):
        result = 1 + 1
    assert result == 2


def test_start_span_creates_span_when_tracer_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With a tracer configured, start_span should emit a named child span."""

    pytest.importorskip("opentelemetry.sdk")
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(tracing, "_tracer", provider.get_tracer("test"))

    with tracing.start_span("model.inference"):
        pass

    span_names = [span.name for span in exporter.get_finished_spans()]
    assert "model.inference" in span_names


def test_fastapi_instrumentation_produces_request_span() -> None:
    """FastAPI instrumentation should produce a server span per request."""

    pytest.importorskip("opentelemetry.instrumentation.fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    try:
        with TestClient(app) as client:
            assert client.get("/ping").status_code == 200
        assert len(exporter.get_finished_spans()) >= 1
    finally:
        FastAPIInstrumentor.uninstrument_app(app)
