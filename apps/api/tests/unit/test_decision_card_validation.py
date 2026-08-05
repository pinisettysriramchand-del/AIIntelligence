from stratiq.application.decisions import validate_card_payload
from stratiq.domain.entities import KPI
from stratiq.domain.exceptions import ValidationError
from uuid import uuid4
import pytest


def test_validate_card_requires_narrative():
    kpi = KPI(
        id=uuid4(),
        document_id=uuid4(),
        owner_id=uuid4(),
        name="Revenue",
        value="10",
        unit="USD",
        period="Q1",
        evidence_chunk_ids=["a"],
    )
    with pytest.raises(ValidationError):
        validate_card_payload({"what_happened": "", "why_it_happened": "x", "recommendation": "y"}, kpi)
