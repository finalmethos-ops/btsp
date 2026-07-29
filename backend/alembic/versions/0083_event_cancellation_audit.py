"""Add event cancellation audit metadata.

Revision ID: 0083_event_cancellation_audit
Revises: 0082_event_order_query_indexes
"""

import sqlalchemy as sa

from alembic import op

revision = "0083_event_cancellation_audit"
down_revision = "0082_event_order_query_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "managed_events",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "managed_events",
        sa.Column("cancelled_by", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "managed_events",
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("managed_events", "cancellation_reason")
    op.drop_column("managed_events", "cancelled_by")
    op.drop_column("managed_events", "cancelled_at")
