"""rename event slide suggested retail to standard cost

Revision ID: 0051_event_slide_standard_cost
Revises: 0050_event_product_slides
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0051_event_slide_standard_cost"
down_revision: str | None = "0050_event_product_slides"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("event_product_slides", "suggested_retail", new_column_name="standard_cost")


def downgrade() -> None:
    op.alter_column("event_product_slides", "standard_cost", new_column_name="suggested_retail")
