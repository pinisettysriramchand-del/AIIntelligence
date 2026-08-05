"""Unit tests for KPI evidence enforcement."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from stratiq.domain.entities import KPI
from stratiq.domain.enums import KPIDomain
from stratiq.domain.exceptions import EvidenceRequiredError


class TestKPIEvidenceEnforcement:
    def _make_kpi(self, evidence_chunk_ids: list[uuid.UUID]) -> KPI:
        return KPI(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            domain=KPIDomain.financial,
            name="Revenue Growth",
            value="15%",
            unit="percent",
            period="Q1 2026",
            evidence_chunk_ids=evidence_chunk_ids,
            raw_extraction={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def test_kpi_with_evidence_is_valid(self):
        chunk_id = uuid.uuid4()
        kpi = self._make_kpi([chunk_id])
        assert kpi.evidence_chunk_ids == [chunk_id]

    def test_kpi_without_evidence_raises_value_error(self):
        with pytest.raises(ValueError, match="must have at least one evidence_chunk_id"):
            self._make_kpi([])

    def test_kpi_with_multiple_evidence_chunks(self):
        ids = [uuid.uuid4() for _ in range(3)]
        kpi = self._make_kpi(ids)
        assert len(kpi.evidence_chunk_ids) == 3

    def test_kpi_domain_values(self):
        for domain in KPIDomain:
            chunk_id = uuid.uuid4()
            kpi = KPI(
                id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                owner_id=uuid.uuid4(),
                domain=domain,
                name=f"KPI for {domain.value}",
                value="100",
                unit=None,
                period=None,
                evidence_chunk_ids=[chunk_id],
                raw_extraction={},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            assert kpi.domain == domain

    def test_evidence_required_error_message(self):
        try:
            self._make_kpi([])
        except ValueError as exc:
            assert "Revenue Growth" in str(exc)
