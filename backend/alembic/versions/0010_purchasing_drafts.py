"""purchasing draft lifecycle

Revision ID: 0010_purchasing_drafts
Revises: 0009_core_purchasing
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_purchasing_drafts"
down_revision: str | None = "0009_core_purchasing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "purchase_requests", sa.Column("revision", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column("purchase_requests", sa.Column("expires_at", sa.DateTime(timezone=True)))
    op.add_column("purchase_requests", sa.Column("cloned_from_id", sa.String(36)))
    op.create_foreign_key(
        "fk_purchase_requests_cloned_from_id",
        "purchase_requests",
        "purchase_requests",
        ["cloned_from_id"],
        ["id"],
    )
    op.create_index("ix_purchase_requests_expires_at", "purchase_requests", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_purchase_requests_expires_at", table_name="purchase_requests")
    op.drop_constraint(
        "fk_purchase_requests_cloned_from_id", "purchase_requests", type_="foreignkey"
    )
    op.drop_column("purchase_requests", "cloned_from_id")
    op.drop_column("purchase_requests", "expires_at")
    op.drop_column("purchase_requests", "revision")
