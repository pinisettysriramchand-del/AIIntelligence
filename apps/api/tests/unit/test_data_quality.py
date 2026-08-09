"""Unit tests for Part 4 Stage 4C data-quality detection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from stratiq.application.data_quality import detect_kpi_quality_issues
from stratiq.domain.entities import KPI
from stratiq.domain.enums import DataQualityCode, KPIDomain


def _kpi(**kwargs) -> KPI:
    now = datetime.now(UTC)
    base = dict(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        domain=KPIDomain.financial,
        name="Revenue",
        value="100",
        unit="USD",
        period="2024-Q1",
        evidence_chunk_ids=[uuid.uuid4()],
        raw_extraction={},
        created_at=now,
        updated_at=now,
    )
    base.update(kwargs)
    return KPI(**base)


def _codes(warnings):
    return {w["code"] for w in warnings}


def test_detects_missing_value_and_period():
    warnings = detect_kpi_quality_issues([_kpi(value="", period=None)])
    assert DataQualityCode.missing_value.value in _codes(warnings)
    assert DataQualityCode.missing_period.value in _codes(warnings)


def test_detects_duplicate_and_conflict():
    a = _kpi(value="100", period="2024-Q1")
    b = _kpi(value="100", period="2024-Q1")
    dups = detect_kpi_quality_issues([a, b])
    assert DataQualityCode.duplicate_record.value in _codes(dups)

    c = _kpi(value="100", period="2024-Q1")
    d = _kpi(value="200", period="2024-Q1")
    conflicts = detect_kpi_quality_issues([c], existing_kpis=[d])
    assert DataQualityCode.conflicting_values.value in _codes(conflicts)


def test_detects_inconsistent_units_and_insufficient_history():
    a = _kpi(unit="USD", period="2024-Q1")
    b = _kpi(unit="EUR", period="2024-Q2")
    warnings = detect_kpi_quality_issues([b], existing_kpis=[a])
    assert DataQualityCode.inconsistent_units.value in _codes(warnings)

    alone = detect_kpi_quality_issues([_kpi()])
    assert DataQualityCode.insufficient_history.value in _codes(alone)


def test_detects_invalid_period_and_missing_unit():
    warnings = detect_kpi_quality_issues([_kpi(period="sometime", unit=None, value="42")])
    assert DataQualityCode.invalid_period.value in _codes(warnings)
    assert DataQualityCode.missing_unit.value in _codes(warnings)
