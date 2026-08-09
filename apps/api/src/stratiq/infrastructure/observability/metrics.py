"""In-process observability metrics for Part 3 (API, AI, processing)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _LatencyStats:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0

    def observe(self, duration_ms: float) -> None:
        self.count += 1
        self.total_ms += duration_ms
        if duration_ms > self.max_ms:
            self.max_ms = duration_ms

    def as_dict(self) -> dict[str, Any]:
        avg = (self.total_ms / self.count) if self.count else 0.0
        return {
            "count": self.count,
            "avg_ms": round(avg, 2),
            "max_ms": round(self.max_ms, 2),
            "total_ms": round(self.total_ms, 2),
        }


@dataclass
class MetricsRegistry:
    """Thread-safe process-local metrics (MVP; not multi-replica aggregated)."""

    _lock: threading.Lock = field(default_factory=threading.Lock)
    _request_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _request_latency: dict[str, _LatencyStats] = field(
        default_factory=lambda: defaultdict(_LatencyStats)
    )
    _error_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _ai_latency: _LatencyStats = field(default_factory=_LatencyStats)
    _ai_tokens: int = 0
    _processing_latency: _LatencyStats = field(default_factory=_LatencyStats)
    _documents_failed: int = 0
    _documents_processed: int = 0
    _retrieval_empty: int = 0
    _retrieval_hits: int = 0

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float) -> None:
        key = f"{method.upper()} {path} {status_code}"
        with self._lock:
            self._request_counts[key] += 1
            self._request_latency[key].observe(duration_ms)
            if status_code >= 400:
                self._error_counts[key] += 1

    def record_ai_call(self, duration_ms: float, tokens: int | None = None) -> None:
        with self._lock:
            self._ai_latency.observe(duration_ms)
            if tokens:
                self._ai_tokens += tokens

    def record_processing(self, duration_ms: float, *, failed: bool) -> None:
        with self._lock:
            self._processing_latency.observe(duration_ms)
            self._documents_processed += 1
            if failed:
                self._documents_failed += 1

    def record_retrieval(self, hit_count: int) -> None:
        with self._lock:
            if hit_count <= 0:
                self._retrieval_empty += 1
            else:
                self._retrieval_hits += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            requests = {
                k: {
                    "count": self._request_counts[k],
                    "latency": self._request_latency[k].as_dict(),
                    "errors": self._error_counts.get(k, 0),
                }
                for k in sorted(self._request_counts.keys())
            }
            return {
                "api": {
                    "requests": requests,
                    "error_total": sum(self._error_counts.values()),
                    "request_total": sum(self._request_counts.values()),
                },
                "ai": {
                    "latency": self._ai_latency.as_dict(),
                    "token_usage_total": self._ai_tokens,
                },
                "processing": {
                    "latency": self._processing_latency.as_dict(),
                    "documents_processed": self._documents_processed,
                    "documents_failed": self._documents_failed,
                },
                "retrieval": {
                    "queries_with_hits": self._retrieval_hits,
                    "queries_empty": self._retrieval_empty,
                },
            }

    def reset(self) -> None:
        with self._lock:
            self._request_counts.clear()
            self._request_latency.clear()
            self._error_counts.clear()
            self._ai_latency = _LatencyStats()
            self._ai_tokens = 0
            self._processing_latency = _LatencyStats()
            self._documents_failed = 0
            self._documents_processed = 0
            self._retrieval_empty = 0
            self._retrieval_hits = 0


_METRICS = MetricsRegistry()


def get_metrics() -> MetricsRegistry:
    return _METRICS


class Timer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0
