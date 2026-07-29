"""loadout teams and vendor booth ready status

Revision ID: 0067_loadout_teams
Revises: 0066_event_settlement_foundation
Create Date: 2026-07-10 08:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0067_loadout_teams"
down_revision: str | None = "0066_event_settlement_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "store_loadout_assignments", sa.Column("team_name", sa.String(255), nullable=True)
    )
    op.add_column(
        "store_loadout_assignments",
        sa.Column("team_member_emails", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "store_loadout_assignments",
        sa.Column("team_lead_emails", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "store_loadout_assignments",
        sa.Column("final_review_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "store_loadout_assignments",
        sa.Column("final_review_requested_by", sa.String(320), nullable=True),
    )
    op.create_index(
        "ix_store_loadout_assignments_team_name",
        "store_loadout_assignments",
        ["team_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_store_loadout_assignments_team_name", table_name="store_loadout_assignments")
    op.drop_column("store_loadout_assignments", "final_review_requested_by")
    op.drop_column("store_loadout_assignments", "final_review_requested_at")
    op.drop_column("store_loadout_assignments", "team_lead_emails")
    op.drop_column("store_loadout_assignments", "team_member_emails")
    op.drop_column("store_loadout_assignments", "team_name")
