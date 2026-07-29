"""vendor hall manual map overrides

Revision ID: 0070_vendor_hall_map_override
Revises: 0069_settlement_decisions
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0070_vendor_hall_map_override"
down_revision: str | None = "0069_settlement_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vendor_hall_booths",
        sa.Column("map_manually_adjusted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("vendor_hall_booths", "map_manually_adjusted")
