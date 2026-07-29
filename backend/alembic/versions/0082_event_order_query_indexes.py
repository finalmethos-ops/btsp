"""Add composite indexes for live event order calculations.

Revision ID: 0082_event_order_query_indexes
Revises: 0081_event_timestamp_integrity
"""

from alembic import op

revision = "0082_event_order_query_indexes"
down_revision = "0081_event_timestamp_integrity"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_event_entity_orders_slide_status", ["slide_id", "status"]),
    (
        "ix_event_entity_orders_sub_event_entity_status",
        ["sub_event_id", "entity_code", "status"],
    ),
    (
        "ix_event_entity_orders_event_entity_status",
        ["event_id", "entity_code", "status"],
    ),
)


def upgrade() -> None:
    for index_name, columns in INDEXES:
        op.create_index(index_name, "event_entity_orders", columns)


def downgrade() -> None:
    for index_name, _columns in reversed(INDEXES):
        op.drop_index(index_name, table_name="event_entity_orders")
