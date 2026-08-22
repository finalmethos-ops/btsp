"""Add aggregate entity and region destinations to purchase requests.

Revision ID: 0122_buy_fair_scope_targets
Revises: 0121_event_order_allocations
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0122_buy_fair_scope_targets"
down_revision: str | None = "0121_event_order_allocations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("purchase_requests", "store_number", existing_type=sa.String(32), nullable=True)
    op.add_column(
        "purchase_requests", sa.Column("target_entity_code", sa.String(64), nullable=True)
    )
    op.add_column(
        "purchase_requests", sa.Column("target_region_code", sa.String(64), nullable=True)
    )
    op.create_index(
        "ix_purchase_requests_target_entity_code",
        "purchase_requests",
        ["target_entity_code"],
    )
    op.create_index(
        "ix_purchase_requests_target_region_code",
        "purchase_requests",
        ["target_region_code"],
    )
    op.create_check_constraint(
        "ck_purchase_request_destination",
        "purchase_requests",
        "store_number IS NOT NULL OR target_entity_code IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_purchase_request_region_entity",
        "purchase_requests",
        "target_region_code IS NULL OR target_entity_code IS NOT NULL",
    )


def downgrade() -> None:
    aggregate_count = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM purchase_requests WHERE store_number IS NULL")
    )
    if aggregate_count:
        raise RuntimeError(
            "Cannot downgrade while aggregate entity or region purchase requests exist"
        )
    op.drop_constraint("ck_purchase_request_region_entity", "purchase_requests", type_="check")
    op.drop_constraint("ck_purchase_request_destination", "purchase_requests", type_="check")
    op.drop_index("ix_purchase_requests_target_region_code", table_name="purchase_requests")
    op.drop_index("ix_purchase_requests_target_entity_code", table_name="purchase_requests")
    op.drop_column("purchase_requests", "target_region_code")
    op.drop_column("purchase_requests", "target_entity_code")
    op.alter_column(
        "purchase_requests", "store_number", existing_type=sa.String(32), nullable=False
    )
