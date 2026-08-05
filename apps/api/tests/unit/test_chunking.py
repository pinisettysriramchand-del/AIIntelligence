from stratiq.application.processing import validate_kpi_payload
from stratiq.domain.exceptions import ValidationError
from stratiq.infrastructure.chunking.semantic import chunk_markdown
import pytest


def test_chunk_markdown_splits_long_text():
    text = "\n\n".join([f"Paragraph {i} " + ("word " * 40) for i in range(8)])
    chunks = chunk_markdown(text, chunk_size=200, overlap=40)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_chunk_markdown_empty():
    assert chunk_markdown("   ") == []


def test_validate_kpi_requires_evidence():
    with pytest.raises(ValidationError):
        validate_kpi_payload({"name": "Revenue", "value": "10"}, known_chunk_ids={"a"})


def test_validate_kpi_accepts_matching_evidence():
    validate_kpi_payload(
        {"name": "Revenue", "value": "10", "evidence_chunk_ids": ["a"]},
        known_chunk_ids={"a", "b"},
    )
