"""Stage 4A: Alembic migration coverage for Decision Intelligence tables."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from stratiq.infrastructure.db.models import Base


def test_orm_registers_di_tables():
    assert "decision_cards" in Base.metadata.tables
    assert "executive_reports" in Base.metadata.tables
    assert "processing_jobs" in Base.metadata.tables


def test_alembic_head_is_007_correlation_ids():
    api_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(api_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(api_root / "alembic"))
    scripts = ScriptDirectory.from_config(cfg)
    heads = scripts.get_heads()
    assert heads == ["007_correlation_ids"]


def test_migration_002_upgrade_sql_contains_di_tables():
    api_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(api_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(api_root / "alembic"))
    cfg.set_main_option(
        "sqlalchemy.url",
        "postgresql+asyncpg://stratiq:stratiq@localhost:5432/stratiq",
    )
    scripts = ScriptDirectory.from_config(cfg)
    rev = scripts.get_revision("002_decision_intelligence")
    assert rev is not None
    assert rev.down_revision == "001_initial"
    source = (api_root / "alembic" / "versions" / "002_decision_intelligence.py").read_text(
        encoding="utf-8"
    )
    assert 'op.create_table(\n        "decision_cards"' in source
    assert 'op.create_table(\n        "executive_reports"' in source
    assert "def downgrade()" in source
    assert 'op.drop_table("decision_cards")' in source
    assert 'op.drop_table("executive_reports")' in source


def test_decision_card_columns_match_orm():
    table = Base.metadata.tables["decision_cards"]
    required = {
        "id",
        "owner_id",
        "kpi_id",
        "document_id",
        "kpi_name",
        "current_value",
        "trend",
        "health",
        "what_happened",
        "why_it_happened",
        "business_impact",
        "risks",
        "opportunities",
        "recommendation",
        "topic",
        "expected_outcome",
        "confidence",
        "evidence_mode",
        "evidence_chunk_ids",
        "related_kpi_ids",
        "created_at",
    }
    assert required.issubset(set(table.c.keys()))


def test_executive_report_columns_match_orm():
    table = Base.metadata.tables["executive_reports"]
    required = {
        "id",
        "owner_id",
        "document_id",
        "summary",
        "health_score",
        "health_label",
        "timeline",
        "confidence",
        "created_at",
    }
    assert required.issubset(set(table.c.keys()))
