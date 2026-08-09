"""Add document quality_warnings (Part 4 Stage 4C).

Revision ID: 004_data_quality
Revises: 003_kpi_intelligence
Create Date: 2026-08-09 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_data_quality"
down_revision: str | None = "003_kpi_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "quality_warnings",
            postgresql.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "quality_warnings")
