import pytest

from stratiq.application.processing import validate_kpi_payload
from stratiq.domain.exceptions import ValidationError


def test_kpi_evidence_must_intersect_known_chunks():
    with pytest.raises(ValidationError):
        validate_kpi_payload(
            {"name": "NPS", "value": "42", "evidence_chunk_ids": ["missing"]},
            known_chunk_ids={"present"},
        )
