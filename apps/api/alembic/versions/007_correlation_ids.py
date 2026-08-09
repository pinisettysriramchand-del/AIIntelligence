"""Add correlation_id to processing_jobs (Part 4 Stage 4F).

Revision ID: 007_correlation_ids
Revises: 006_processing_jobs
Create Date: 2026-08-09 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_correlation_ids"
down_revision: str | None = "006_processing_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "processing_jobs",
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_processing_jobs_correlation_id", "processing_jobs", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_processing_jobs_correlation_id", table_name="processing_jobs")
    op.drop_column("processing_jobs", "correlation_id")
