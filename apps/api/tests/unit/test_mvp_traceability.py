"""Stage 4J: MVP traceability matrix presence and required mappings."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MATRIX = ROOT / "docs" / "MVP_TRACEABILITY_MATRIX.md"

REQUIRED_HEADERS = (
    "Product requirement",
    "Architecture component",
    "API / UI module",
    "Test",
    "Acceptance criterion",
)

REQUIRED_IDS = (
    "PR-18.1",
    "PR-20.1",
    "PR-21",
    "PR-22.2",
    "PR-24.1",
    "PR-25.1",
    "PR-26",
    "PR-27",
    "PR-UI.1",
    "PR-AI.1",
    "PR-CORE.1",
)


def test_traceability_matrix_exists_with_mapping_columns():
    assert MATRIX.is_file(), "docs/MVP_TRACEABILITY_MATRIX.md missing"
    text = MATRIX.read_text(encoding="utf-8")
    for header in REQUIRED_HEADERS:
        assert header in text, f"matrix missing column/header: {header}"


def test_traceability_matrix_covers_major_mvp_ids():
    text = MATRIX.read_text(encoding="utf-8")
    missing = [rid for rid in REQUIRED_IDS if rid not in text]
    assert not missing, f"matrix missing requirement ids: {missing}"


def test_section_27_self_maps():
    text = MATRIX.read_text(encoding="utf-8")
    assert "PR-27" in text
    assert "MVP_TRACEABILITY_MATRIX.md" in text
    assert "test_mvp_traceability.py" in text
