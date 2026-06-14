"""OpenTelemetry distributed tracing for FAANG-grade observability."""
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import Request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from backend.config import settings

logger = logging.getLogger(__name__)

_tracer: trace.Tracer | None = None


def setup_tracing(app, service_name: str = "hospitaliq-backend"):
    resource = Resource.create({"service.name": service_name, "service.version": "2.0.0"})
    provider = TracerProvider(resource=resource)

    # If OTLP endpoint configured, export traces
    if settings.otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"OpenTelemetry exporting traces to {settings.otlp_endpoint}")
    else:
        logger.info("OpenTelemetry tracing enabled (no OTLP endpoint configured)")

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

    global _tracer
    _tracer = trace.get_tracer(service_name)
    return _tracer


def get_tracer() -> trace.Tracer:
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer("hospitaliq-backend")
    return _tracer


@contextmanager
def trace_span(name: str, attributes: dict = None) -> Iterator[trace.Span]:
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            span.set_attributes(attributes)
        yield span


def get_request_attributes(request: Request) -> dict:
    return {
        "http.method": request.method,
        "http.url": str(request.url),
        "http.host": request.client.host if request.client else "unknown",
        "http.user_agent": request.headers.get("user-agent", ""),
    }
