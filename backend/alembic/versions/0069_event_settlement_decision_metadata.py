"""event settlement decision metadata

Revision ID: 0069_settlement_decisions
Revises: 0068_loadout_review
Create Date: 2026-07-10 09:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0069_settlement_decisions"
down_revision: str | None = "0068_loadout_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "event_settlement_events",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_settlement_events",
        sa.Column("approved_by", sa.String(320), nullable=True),
    )
    op.add_column(
        "event_settlement_events",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_settlement_events",
        sa.Column("closed_by", sa.String(320), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_settlement_events", "closed_by")
    op.drop_column("event_settlement_events", "closed_at")
    op.drop_column("event_settlement_events", "approved_by")
    op.drop_column("event_settlement_events", "approved_at")
