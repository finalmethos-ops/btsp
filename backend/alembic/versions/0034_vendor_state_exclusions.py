"""vendor geographical state exclusions

Revision ID: 0034_vendor_states
Revises: 0033_vendor_moq
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0034_vendor_states"
down_revision: str | None = "0033_vendor_moq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendor_state_exclusions",
        sa.Column("vendor_code", sa.String(64), primary_key=True),
        sa.Column("state_code", sa.String(2), primary_key=True),
        sa.ForeignKeyConstraint(
            ["vendor_code"], ["catalog_vendors.vendor_code"], ondelete="CASCADE"
        ),
    )


def downgrade() -> None:
    op.drop_table("vendor_state_exclusions")
