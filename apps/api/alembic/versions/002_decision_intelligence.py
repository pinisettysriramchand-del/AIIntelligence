"""Add decision_cards and executive_reports tables.

Revision ID: 002_decision_intelligence
Revises: 001_initial
Create Date: 2026-08-09 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_decision_intelligence"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kpi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kpi_name", sa.String(512), nullable=False),
        sa.Column("current_value", sa.String(512), nullable=False),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("period", sa.String(128), nullable=True),
        sa.Column("domain", sa.String(64), nullable=True),
        sa.Column("trend", sa.String(32), nullable=False),
        sa.Column("health", sa.String(32), nullable=False),
        sa.Column("what_happened", sa.Text(), nullable=False),
        sa.Column("why_it_happened", sa.Text(), nullable=False),
        sa.Column("business_impact", sa.Text(), nullable=False, server_default=""),
        sa.Column("risks", postgresql.JSON(), nullable=False),
        sa.Column("opportunities", postgresql.JSON(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("forecast_value", sa.String(255), nullable=True),
        sa.Column("forecast_horizon", sa.String(128), nullable=True),
        sa.Column("forecast_explanation", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(32), nullable=False, server_default="0.5"),
        sa.Column("evidence_mode", sa.String(32), nullable=False, server_default="evidence"),
        sa.Column("evidence_chunk_ids", postgresql.JSON(), nullable=False),
        sa.Column("related_kpi_ids", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kpi_id"], ["kpis.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_cards_owner_id", "decision_cards", ["owner_id"])
    op.create_index("ix_decision_cards_kpi_id", "decision_cards", ["kpi_id"])
    op.create_index("ix_decision_cards_document_id", "decision_cards", ["document_id"])

    op.create_table(
        "executive_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("health_score", sa.Integer(), nullable=False),
        sa.Column("health_label", sa.String(32), nullable=False),
        sa.Column("timeline", postgresql.JSON(), nullable=False),
        sa.Column("confidence", sa.String(32), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_executive_reports_owner_id", "executive_reports", ["owner_id"])
    op.create_index("ix_executive_reports_document_id", "executive_reports", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_executive_reports_document_id", table_name="executive_reports")
    op.drop_index("ix_executive_reports_owner_id", table_name="executive_reports")
    op.drop_table("executive_reports")
    op.drop_index("ix_decision_cards_document_id", table_name="decision_cards")
    op.drop_index("ix_decision_cards_kpi_id", table_name="decision_cards")
    op.drop_index("ix_decision_cards_owner_id", table_name="decision_cards")
    op.drop_table("decision_cards")
