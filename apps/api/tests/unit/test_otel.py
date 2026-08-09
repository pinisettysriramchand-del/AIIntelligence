"""OpenTelemetry setup unit tests."""

from __future__ import annotations

from stratiq.config import Settings
from stratiq.infrastructure.observability import get_metrics
from stratiq.infrastructure.observability import otel as otel_mod


def test_setup_otel_disabled_by_default():
    settings = Settings(otel_enabled=False)
    # Force clean module state for this process-local flag
    otel_mod._INITIALIZED = False
    assert otel_mod.setup_otel(settings) is False
    assert otel_mod.is_otel_enabled() is False


def test_setup_otel_enabled_without_endpoint():
    settings = Settings(
        otel_enabled=True,
        otel_service_name="stratiq-test",
        otel_exporter_otlp_endpoint="",
        otel_traces_sampler_ratio=1.0,
    )
    otel_mod._INITIALIZED = False
    assert otel_mod.setup_otel(settings) is True
    assert otel_mod.is_otel_enabled() is True

    get_metrics().record_ai_call(12.0, tokens=10)
    get_metrics().record_processing(20.0, failed=False)
    get_metrics().record_retrieval(0)
    snap = get_metrics().snapshot()
    assert snap["ai"]["token_usage_total"] >= 10
