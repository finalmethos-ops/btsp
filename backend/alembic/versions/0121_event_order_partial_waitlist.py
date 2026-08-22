"""Track confirmed and waitlisted event quantities independently."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0121_event_order_partial_waitlist"
down_revision: str | None = "0120_event_order_variant_qty"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _allocation_columns(table: str, *, include_costs: bool) -> None:
    op.add_column(
        table,
        sa.Column("confirmed_quantity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        table,
        sa.Column("waitlisted_quantity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        table,
        sa.Column("confirmed_variant_quantities", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        table,
        sa.Column("waitlisted_variant_quantities", sa.JSON(), nullable=False, server_default="{}"),
    )
    if include_costs:
        op.add_column(
            table,
            sa.Column(
                "confirmed_total_cost", sa.Numeric(16, 2), nullable=False, server_default="0"
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "waitlisted_total_cost", sa.Numeric(16, 2), nullable=False, server_default="0"
            ),
        )


def upgrade() -> None:
    _allocation_columns("event_entity_orders", include_costs=True)
    _allocation_columns("event_entity_order_revisions", include_costs=False)
    op.execute(
        """
        UPDATE event_entity_orders
        SET confirmed_quantity = quantity,
            confirmed_variant_quantities = variant_quantities,
            confirmed_total_cost = total_cost
        WHERE status = 'confirmed'
        """
    )
    op.execute(
        """
        UPDATE event_entity_orders
        SET waitlisted_quantity = quantity,
            waitlisted_variant_quantities = variant_quantities,
            waitlisted_total_cost = total_cost
        WHERE status = 'waitlisted'
        """
    )
    op.execute(
        """
        UPDATE event_entity_order_revisions
        SET confirmed_quantity = quantity,
            confirmed_variant_quantities = variant_quantities
        WHERE status <> 'waitlisted'
        """
    )
    op.execute(
        """
        UPDATE event_entity_order_revisions
        SET waitlisted_quantity = quantity,
            waitlisted_variant_quantities = variant_quantities
        WHERE status = 'waitlisted'
        """
    )


def downgrade() -> None:
    for table in ("event_entity_order_revisions", "event_entity_orders"):
        op.drop_column(table, "waitlisted_variant_quantities")
        op.drop_column(table, "confirmed_variant_quantities")
        op.drop_column(table, "waitlisted_quantity")
        op.drop_column(table, "confirmed_quantity")
    op.drop_column("event_entity_orders", "waitlisted_total_cost")
    op.drop_column("event_entity_orders", "confirmed_total_cost")
