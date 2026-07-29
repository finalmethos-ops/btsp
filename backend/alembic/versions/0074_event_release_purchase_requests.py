"""link event release lines to purchasing requests

Revision ID: 0074_event_release_requests
Revises: 0073_event_variant_release
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0074_event_release_requests"
down_revision: str | None = "0073_event_variant_release"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "event_order_release_lines",
        sa.Column(
            "purchase_request_id",
            sa.String(36),
            sa.ForeignKey("purchase_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_event_order_release_lines_purchase_request_id",
        "event_order_release_lines",
        ["purchase_request_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_order_release_lines_purchase_request_id",
        table_name="event_order_release_lines",
    )
    op.drop_column("event_order_release_lines", "purchase_request_id")
