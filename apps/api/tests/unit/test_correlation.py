"""Stage 4F: correlation ID helpers."""

from __future__ import annotations

from stratiq.infrastructure.observability.correlation import (
    CorrelationLogFilter,
    bind_correlation,
    correlation_attrs,
    ensure_correlation_id,
    get_correlation_id,
    get_job_id,
    resolve_incoming_request_id,
    set_correlation_id,
)


def test_resolve_incoming_prefers_x_request_id():
    headers = {"X-Request-ID": "req-123", "X-Correlation-ID": "corr-999"}
    assert resolve_incoming_request_id(headers) == "req-123"


def test_resolve_incoming_falls_back_to_correlation_header():
    headers = {"X-Correlation-ID": "corr-999"}
    assert resolve_incoming_request_id(headers) == "corr-999"


def test_resolve_incoming_generates_when_missing():
    value = resolve_incoming_request_id({})
    assert len(value) >= 8


def test_bind_correlation_sets_context_and_attrs():
    with bind_correlation(correlation_id="abc", job_id="job-1"):
        assert get_correlation_id() == "abc"
        assert get_job_id() == "job-1"
        attrs = correlation_attrs()
        assert attrs["stratiq.correlation_id"] == "abc"
        assert attrs["stratiq.job_id"] == "job-1"
    assert get_correlation_id() is None
    assert get_job_id() is None


def test_ensure_correlation_id_reuses_existing():
    set_correlation_id("fixed-id")
    assert ensure_correlation_id() == "fixed-id"
    set_correlation_id(None)


def test_log_filter_attaches_fields():
    with bind_correlation(correlation_id="cid", job_id="jid"):
        record = type("R", (), {})()
        assert CorrelationLogFilter().filter(record) is True
        assert record.correlation_id == "cid"
        assert record.job_id == "jid"
