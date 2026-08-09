"""Unit tests for Part 4 Stage 4B KPI intelligence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from stratiq.application.kpi_intelligence import (
    compute_trend,
    enrich_kpis_with_comparisons,
    normalize_extraction_fields,
    parse_numeric,
)
from stratiq.domain.entities import KPI
from stratiq.domain.enums import KPIDomain, TrendDirection


def _kpi(name: str, value: str, period: str, unit: str = "USD") -> KPI:
    now = datetime.now(UTC)
    return KPI(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        domain=KPIDomain.financial,
        name=name,
        value=value,
        unit=unit,
        period=period,
        evidence_chunk_ids=[uuid.uuid4()],
        raw_extraction={},
        created_at=now,
        updated_at=now,
    )


def test_parse_numeric_strips_symbols():
    assert parse_numeric("$1,200.5") == 1200.5
    assert parse_numeric("15%") == 15.0
    assert parse_numeric("n/a") is None


def test_compute_trend_up_down_flat():
    assert compute_trend("120", "100")[0] == TrendDirection.up
    assert compute_trend("80", "100")[0] == TrendDirection.down
    assert compute_trend("100", "100")[0] == TrendDirection.flat


def test_enrich_persists_previous_and_delta():
    k1 = _kpi("Revenue", "100", "2024-Q1")
    k2 = _kpi("Revenue", "120", "2024-Q2")
    enrich_kpis_with_comparisons([k1, k2])
    assert k1.previous_value is None
    assert k2.previous_value == "100"
    assert k2.previous_period == "2024-Q1"
    assert k2.trend == TrendDirection.up
    assert k2.delta_label and k2.delta_label.startswith("+")


def test_normalize_extraction_fields():
    out = normalize_extraction_fields(
        {
            "business_meaning": "Top-line sales",
            "confidence": "0.8",
            "dimensions": ["EMEA"],
        }
    )
    assert out["business_meaning"] == "Top-line sales"
    assert out["confidence"] == 0.8
    assert out["dimensions"] == {"tags": ["EMEA"]}
