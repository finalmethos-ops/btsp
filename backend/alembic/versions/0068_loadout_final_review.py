"""store loadout final review metadata

Revision ID: 0068_loadout_review
Revises: 0067_loadout_teams
Create Date: 2026-07-10 09:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0068_loadout_review"
down_revision: str | None = "0067_loadout_teams"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "store_loadout_assignments",
        sa.Column("final_review_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "store_loadout_assignments",
        sa.Column("final_review_completed_by", sa.String(320), nullable=True),
    )
    op.add_column(
        "store_loadout_assignments",
        sa.Column("final_review_notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("store_loadout_assignments", "final_review_notes")
    op.drop_column("store_loadout_assignments", "final_review_completed_by")
    op.drop_column("store_loadout_assignments", "final_review_completed_at")
