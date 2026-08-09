"""OpenTelemetry tracing + metrics setup (OTLP HTTP export)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from opentelemetry import metrics, trace
from opentelemetry.sdk.resources import Resource

if TYPE_CHECKING:
    from fastapi import FastAPI
    from stratiq.config import Settings

logger = logging.getLogger(__name__)

_INITIALIZED = False
_METER = None
_TRACER = None

# Instruments (lazy after setup)
_ai_latency_hist = None
_ai_tokens_counter = None
_processing_latency_hist = None
_documents_processed_counter = None
_documents_failed_counter = None
_retrieval_hits_counter = None
_retrieval_empty_counter = None


def setup_otel(settings: "Settings") -> bool:
    """Configure global TracerProvider/MeterProvider when enabled.

    Returns True if OTEL was initialized.
    """
    global _INITIALIZED, _METER, _TRACER
    global _ai_latency_hist, _ai_tokens_counter
    global _processing_latency_hist, _documents_processed_counter, _documents_failed_counter
    global _retrieval_hits_counter, _retrieval_empty_counter

    if _INITIALIZED:
        return True
    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled (set OTEL_ENABLED=true to enable)")
        return False

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "1.0.0",
            "deployment.environment": "debug" if settings.debug else "production",
        }
    )

    endpoint = (settings.otel_exporter_otlp_endpoint or "").rstrip("/")
    trace_provider = _build_tracer_provider(resource, endpoint, settings.otel_traces_sampler_ratio)
    meter_provider = _build_meter_provider(resource, endpoint)

    trace.set_tracer_provider(trace_provider)
    metrics.set_meter_provider(meter_provider)

    _TRACER = trace.get_tracer("stratiq")
    _METER = metrics.get_meter("stratiq")

    _ai_latency_hist = _METER.create_histogram(
        "stratiq.ai.latency_ms",
        unit="ms",
        description="LLM call latency",
    )
    _ai_tokens_counter = _METER.create_counter(
        "stratiq.ai.tokens",
        unit="1",
        description="LLM token usage",
    )
    _processing_latency_hist = _METER.create_histogram(
        "stratiq.processing.latency_ms",
        unit="ms",
        description="Document processing duration",
    )
    _documents_processed_counter = _METER.create_counter(
        "stratiq.documents.processed",
        description="Documents processed",
    )
    _documents_failed_counter = _METER.create_counter(
        "stratiq.documents.failed",
        description="Documents failed processing",
    )
    _retrieval_hits_counter = _METER.create_counter(
        "stratiq.retrieval.hits",
        description="RAG queries with hits",
    )
    _retrieval_empty_counter = _METER.create_counter(
        "stratiq.retrieval.empty",
        description="RAG queries with no hits",
    )

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception as exc:  # pragma: no cover
        logger.warning("httpx instrumentation skipped: %s", exc)

    _INITIALIZED = True
    logger.info(
        "OpenTelemetry enabled",
        extra={"endpoint": endpoint or "(no OTLP export)", "service": settings.otel_service_name},
    )
    return True


def instrument_fastapi(app: "FastAPI") -> None:
    if not _INITIALIZED:
        return
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,metrics,docs,openapi.json,redoc",
    )


def record_ai_otel(duration_ms: float, tokens: int | None = None) -> None:
    if not _INITIALIZED:
        return
    from stratiq.infrastructure.observability.correlation import correlation_attrs

    attrs = correlation_attrs()
    assert _ai_latency_hist is not None
    _ai_latency_hist.record(duration_ms, attributes=attrs or None)
    if tokens and _ai_tokens_counter is not None:
        _ai_tokens_counter.add(tokens, attributes=attrs or None)


def record_processing_otel(duration_ms: float, *, failed: bool) -> None:
    if not _INITIALIZED:
        return
    from stratiq.infrastructure.observability.correlation import correlation_attrs

    attrs = correlation_attrs()
    assert _processing_latency_hist is not None
    _processing_latency_hist.record(duration_ms, attributes=attrs or None)
    assert _documents_processed_counter is not None
    _documents_processed_counter.add(1, attributes=attrs or None)
    if failed and _documents_failed_counter is not None:
        _documents_failed_counter.add(1, attributes=attrs or None)


def record_retrieval_otel(hit_count: int) -> None:
    if not _INITIALIZED:
        return
    from stratiq.infrastructure.observability.correlation import correlation_attrs

    attrs = correlation_attrs()
    if hit_count <= 0:
        assert _retrieval_empty_counter is not None
        _retrieval_empty_counter.add(1, attributes=attrs or None)
    else:
        assert _retrieval_hits_counter is not None
        _retrieval_hits_counter.add(1, attributes=attrs or None)


def is_otel_enabled() -> bool:
    return _INITIALIZED


def get_tracer() -> Any:
    return _TRACER or trace.get_tracer("stratiq")


def _build_tracer_provider(resource: Resource, endpoint: str, sample_ratio: float):
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

    ratio = max(0.0, min(1.0, sample_ratio))
    provider = TracerProvider(
        resource=resource,
        sampler=ParentBasedTraceIdRatio(ratio),
    )
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
    # Without an endpoint, spans remain in-process (no export) until OTLP is configured.
    return provider


def _build_meter_provider(resource: Resource, endpoint: str):
    from opentelemetry.sdk.metrics import MeterProvider

    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
            export_interval_millis=15000,
        )
        return MeterProvider(resource=resource, metric_readers=[reader])

    # No OTLP endpoint: in-memory meter provider (instruments still record).
    return MeterProvider(resource=resource)
