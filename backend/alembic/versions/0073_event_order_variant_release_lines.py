"""allow multiple released model lines per event order

Revision ID: 0073_event_variant_release
Revises: 0072_event_order_windows
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0073_event_variant_release"
down_revision: str | None = "0072_event_order_windows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "event_order_release_lines_order_id_key",
        "event_order_release_lines",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "event_order_release_lines_order_id_key",
        "event_order_release_lines",
        ["order_id"],
    )
