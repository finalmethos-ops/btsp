"""Preserve product-specific quantities in event order revisions."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0120_event_order_variant_qty"
down_revision: str | None = "0119_event_slide_vendor_logos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "event_entity_order_revisions",
        sa.Column(
            "variant_quantities",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("event_entity_order_revisions", "variant_quantities")
