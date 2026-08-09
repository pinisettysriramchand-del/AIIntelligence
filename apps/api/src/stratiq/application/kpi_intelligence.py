"""Deterministic KPI intelligence helpers (Part 4 §24)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from stratiq.domain.entities import KPI
from stratiq.domain.enums import TrendDirection


def parse_numeric(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = (
        str(value)
        .strip()
        .replace(",", "")
        .replace("%", "")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
    )
    try:
        return float(cleaned)
    except ValueError:
        return None


def compute_trend(current: str | None, previous: str | None) -> tuple[TrendDirection, str | None]:
    cur = parse_numeric(current)
    prev = parse_numeric(previous)
    if cur is None or prev is None:
        return TrendDirection.unknown, None
    delta = cur - prev
    if abs(delta) < 1e-12:
        return TrendDirection.flat, "0"
    direction = TrendDirection.up if delta > 0 else TrendDirection.down
    return direction, f"{delta:+.4g}"


def enrich_kpis_with_comparisons(
    new_kpis: list[KPI],
    existing_kpis: list[KPI] | None = None,
) -> list[KPI]:
    """Persist prior-period / trend when multiple same-name+unit observations exist.

    Deterministic when values parse as numbers; otherwise leaves trend=unknown.
    """
    pool = list(existing_kpis or []) + list(new_kpis)
    groups: dict[tuple[str, str], list[KPI]] = defaultdict(list)
    for kpi in pool:
        key = (kpi.name.strip().lower(), (kpi.unit or "").strip().lower())
        groups[key].append(kpi)

    by_id = {k.id: k for k in new_kpis}
    for group in groups.values():
        ordered = sorted(group, key=lambda k: (k.period or "", str(k.created_at), str(k.id)))
        for idx, kpi in enumerate(ordered):
            if kpi.id not in by_id:
                continue
            if idx == 0:
                kpi.previous_value = None
                kpi.previous_period = None
                kpi.trend = TrendDirection.unknown
                kpi.delta_label = None
                continue
            prev = ordered[idx - 1]
            kpi.previous_value = prev.value
            kpi.previous_period = prev.period
            trend, delta = compute_trend(kpi.value, prev.value)
            kpi.trend = trend
            kpi.delta_label = delta
    return new_kpis


def normalize_extraction_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Map LLM/tabular extraction fields into Part 4 KPI intelligence shape."""
    meaning = raw.get("business_meaning") or raw.get("meaning") or raw.get("description")
    conf = raw.get("confidence")
    try:
        confidence = float(conf) if conf is not None else 0.5
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    dimensions = raw.get("dimensions") or raw.get("related_dimensions") or {}
    if isinstance(dimensions, list):
        dimensions = {"tags": dimensions}
    if not isinstance(dimensions, dict):
        dimensions = {}

    return {
        "business_meaning": str(meaning).strip() if meaning else None,
        "confidence": confidence,
        "dimensions": dimensions,
    }
