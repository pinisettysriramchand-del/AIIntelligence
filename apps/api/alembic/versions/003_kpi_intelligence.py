"""Add KPI intelligence fields (Part 4 Stage 4B).

Revision ID: 003_kpi_intelligence
Revises: 002_decision_intelligence
Create Date: 2026-08-09 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_kpi_intelligence"
down_revision: str | None = "002_decision_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("kpis", sa.Column("business_meaning", sa.Text(), nullable=True))
    op.add_column(
        "kpis",
        sa.Column("confidence", sa.String(32), nullable=False, server_default="0.5"),
    )
    op.add_column(
        "kpis",
        sa.Column("dimensions", postgresql.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.add_column("kpis", sa.Column("previous_value", sa.String(512), nullable=True))
    op.add_column("kpis", sa.Column("previous_period", sa.String(128), nullable=True))
    op.add_column(
        "kpis",
        sa.Column("trend", sa.String(32), nullable=False, server_default="unknown"),
    )
    op.add_column("kpis", sa.Column("delta_label", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("kpis", "delta_label")
    op.drop_column("kpis", "trend")
    op.drop_column("kpis", "previous_period")
    op.drop_column("kpis", "previous_value")
    op.drop_column("kpis", "dimensions")
    op.drop_column("kpis", "confidence")
    op.drop_column("kpis", "business_meaning")
