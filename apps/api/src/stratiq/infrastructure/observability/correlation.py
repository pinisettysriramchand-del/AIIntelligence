"""Request/job correlation IDs for logs, workers, and OTEL spans (Part 4 Stage 4F)."""

from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Iterator

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"

_correlation_id: ContextVar[str | None] = ContextVar("stratiq_correlation_id", default=None)
_job_id: ContextVar[str | None] = ContextVar("stratiq_job_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def get_job_id() -> str | None:
    return _job_id.get()


def set_correlation_id(value: str | None) -> Token:
    return _correlation_id.set(value)


def set_job_id(value: str | None) -> Token:
    return _job_id.set(value)


def reset_correlation_id(token: Token) -> None:
    _correlation_id.reset(token)


def reset_job_id(token: Token) -> None:
    _job_id.reset(token)


def ensure_correlation_id() -> str:
    current = get_correlation_id()
    if current:
        return current
    generated = str(uuid.uuid4())
    set_correlation_id(generated)
    return generated


def correlation_attrs() -> dict[str, str]:
    attrs: dict[str, str] = {}
    cid = get_correlation_id()
    jid = get_job_id()
    if cid:
        attrs["stratiq.correlation_id"] = cid
        attrs["stratiq.request_id"] = cid
    if jid:
        attrs["stratiq.job_id"] = jid
    return attrs


def apply_to_current_span() -> None:
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span is None or not span.is_recording():
            return
        for key, value in correlation_attrs().items():
            span.set_attribute(key, value)
    except Exception:  # pragma: no cover
        return


@contextmanager
def bind_correlation(
    *,
    correlation_id: str | None = None,
    job_id: str | None = None,
) -> Iterator[None]:
    cid_token: Token | None = None
    jid_token: Token | None = None
    try:
        if correlation_id is not None:
            cid_token = set_correlation_id(correlation_id)
        if job_id is not None:
            jid_token = set_job_id(job_id)
        apply_to_current_span()
        yield
    finally:
        if jid_token is not None:
            reset_job_id(jid_token)
        if cid_token is not None:
            reset_correlation_id(cid_token)


class CorrelationLogFilter(logging.Filter):
    """Attach correlation_id / job_id onto every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"  # type: ignore[attr-defined]
        record.job_id = get_job_id() or "-"  # type: ignore[attr-defined]
        return True


def install_log_filter(logger_name: str | None = None) -> None:
    target = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    for existing in target.filters:
        if isinstance(existing, CorrelationLogFilter):
            return
    target.addFilter(CorrelationLogFilter())


def resolve_incoming_request_id(headers: Any) -> str:
    """Pick client-supplied request/correlation id or generate one."""
    for key in (REQUEST_ID_HEADER, CORRELATION_ID_HEADER, REQUEST_ID_HEADER.lower(), "x-correlation-id"):
        try:
            value = headers.get(key)
        except Exception:
            value = None
        if value:
            text = str(value).strip()
            if text:
                return text[:128]
    return str(uuid.uuid4())
