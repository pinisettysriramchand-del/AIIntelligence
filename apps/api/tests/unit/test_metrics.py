"""Unit tests for process-local observability metrics."""

from __future__ import annotations

from stratiq.infrastructure.observability.metrics import MetricsRegistry


def test_metrics_records_requests_and_errors():
    m = MetricsRegistry()
    m.record_request("GET", "/health", 200, 12.5)
    m.record_request("GET", "/api/v1/kpis", 500, 40.0)
    snap = m.snapshot()
    assert snap["api"]["request_total"] == 2
    assert snap["api"]["error_total"] == 1
    assert snap["api"]["requests"]["GET /health 200"]["latency"]["count"] == 1


def test_metrics_records_ai_processing_retrieval():
    m = MetricsRegistry()
    m.record_ai_call(100.0, tokens=250)
    m.record_processing(500.0, failed=False)
    m.record_processing(200.0, failed=True)
    m.record_retrieval(3)
    m.record_retrieval(0)
    snap = m.snapshot()
    assert snap["ai"]["token_usage_total"] == 250
    assert snap["ai"]["latency"]["count"] == 1
    assert snap["processing"]["documents_processed"] == 2
    assert snap["processing"]["documents_failed"] == 1
    assert snap["retrieval"]["queries_with_hits"] == 1
    assert snap["retrieval"]["queries_empty"] == 1
