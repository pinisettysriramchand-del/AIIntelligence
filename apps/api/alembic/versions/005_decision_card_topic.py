"""Add Decision Card topic and expected_outcome (Part 4 Stage 4D).

Revision ID: 005_decision_card_topic
Revises: 004_data_quality
Create Date: 2026-08-09 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_decision_card_topic"
down_revision: str | None = "004_data_quality"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "decision_cards",
        sa.Column("topic", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "decision_cards",
        sa.Column("expected_outcome", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("decision_cards", "expected_outcome")
    op.drop_column("decision_cards", "topic")
