"""Unit tests for Decision Intelligence helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from stratiq.application.decisions import validate_card_payload
from stratiq.application.health import compute_health_score
from stratiq.domain.entities import DecisionCard, KPI
from stratiq.domain.enums import EvidenceMode, HealthLabel, KPIDomain, TrendDirection
from stratiq.domain.exceptions import ValidationError


def test_validate_card_requires_narrative():
    now = datetime.now(UTC)
    kpi = KPI(
        id=uuid4(),
        document_id=uuid4(),
        owner_id=uuid4(),
        domain=KPIDomain.financial,
        name="Revenue",
        value="10",
        unit="USD",
        period="Q1",
        evidence_chunk_ids=[uuid4()],
        raw_extraction={},
        created_at=now,
        updated_at=now,
    )
    with pytest.raises(ValidationError):
        validate_card_payload(
            {"what_happened": "", "why_it_happened": "x", "recommendation": "y"},
            kpi,
        )


def test_compute_health_score_labels():
    cards = [
        DecisionCard(
            id=uuid4(),
            owner_id=uuid4(),
            kpi_id=uuid4(),
            document_id=uuid4(),
            kpi_name="Revenue",
            current_value="100",
            unit="USD",
            period="Q1",
            domain="financial",
            trend=TrendDirection.up,
            health=HealthLabel.healthy,
            what_happened="x",
            why_it_happened="y",
            business_impact="Stable revenue base",
            risks=[],
            opportunities=[],
            recommendation="z",
            forecast_value="110",
            forecast_horizon="Q2",
            forecast_explanation="growth",
            confidence=0.8,
            evidence_mode=EvidenceMode.evidence,
            evidence_chunk_ids=[uuid4()],
        )
    ]
    score, label = compute_health_score(cards, ready_documents=2, failed_documents=0, llm_score=80)
    assert 0 <= score <= 100
    assert label in {HealthLabel.healthy, HealthLabel.watch, HealthLabel.critical}
