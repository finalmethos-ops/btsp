"""event slide product variants

Revision ID: 0071_event_slide_variants
Revises: 0070_vendor_hall_map_override
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0071_event_slide_variants"
down_revision: str | None = "0070_vendor_hall_map_override"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "event_product_slides",
        sa.Column("product_variants", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "event_entity_orders",
        sa.Column("variant_quantities", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("event_entity_orders", "variant_quantities")
    op.drop_column("event_product_slides", "product_variants")
