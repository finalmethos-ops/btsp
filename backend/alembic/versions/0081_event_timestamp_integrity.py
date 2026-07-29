"""Enforce required event-domain audit timestamps.

Revision ID: 0081_event_timestamp_integrity
Revises: 0080_sub_event_end_index
"""

import sqlalchemy as sa

from alembic import op

revision = "0081_event_timestamp_integrity"
down_revision = "0080_sub_event_end_index"
branch_labels = None
depends_on = None

TIMESTAMP_COLUMNS = (
    ("event_announcements", "created_at"),
    ("event_announcements", "updated_at"),
    ("event_attendance", "updated_at"),
    ("event_branding_assets", "uploaded_at"),
    ("event_calendar_entries", "created_at"),
    ("event_calendar_entries", "updated_at"),
    ("event_entity_order_revisions", "changed_at"),
    ("event_entity_orders", "submitted_at"),
    ("event_entity_orders", "updated_at"),
    ("event_memberships", "created_at"),
    ("event_order_release_batches", "created_at"),
    ("event_order_review_events", "created_at"),
    ("event_poll_votes", "created_at"),
    ("event_polls", "created_at"),
    ("event_presentation_states", "updated_at"),
    ("event_product_slide_images", "uploaded_at"),
    ("event_product_slides", "created_at"),
    ("event_product_slides", "updated_at"),
    ("event_settlement_audit_log", "created_at"),
    ("event_settlement_events", "created_at"),
    ("event_settlement_events", "updated_at"),
    ("event_settlement_exceptions", "created_at"),
    ("event_staff_tasks", "created_at"),
    ("event_staff_tasks", "updated_at"),
    ("event_sub_event_registrations", "assigned_at"),
    ("event_vendor_booths", "created_at"),
    ("event_vendor_booths", "updated_at"),
    ("managed_events", "created_at"),
    ("managed_events", "updated_at"),
    ("managed_sub_events", "created_at"),
    ("store_loadout_assignments", "created_at"),
    ("store_loadout_assignments", "updated_at"),
    ("store_loadout_audit_log", "created_at"),
    ("store_loadout_events", "created_at"),
    ("store_loadout_events", "updated_at"),
    ("store_loadout_item_checkins", "checked_at"),
    ("store_loadout_items", "created_at"),
    ("store_loadout_items", "updated_at"),
    ("store_loadout_signoffs", "signed_at"),
    ("vendor_hall_audit_log", "created_at"),
    ("vendor_hall_booth_checkins", "started_at"),
    ("vendor_hall_booths", "created_at"),
    ("vendor_hall_booths", "updated_at"),
    ("vendor_hall_events", "created_at"),
    ("vendor_hall_events", "updated_at"),
    ("vendor_hall_exceptions", "created_at"),
    ("vendor_hall_floor_maps", "uploaded_at"),
    ("vendor_hall_inventory_imports", "uploaded_at"),
    ("vendor_hall_inventory_items", "created_at"),
    ("vendor_hall_inventory_items", "updated_at"),
    ("vendor_hall_item_attachments", "uploaded_at"),
    ("vendor_hall_item_checkins", "checked_at"),
)


def upgrade() -> None:
    timestamp_type = sa.DateTime(timezone=True)
    for table_name, column_name in TIMESTAMP_COLUMNS:
        op.execute(
            sa.text(
                f'UPDATE "{table_name}" SET "{column_name}" = CURRENT_TIMESTAMP '
                f'WHERE "{column_name}" IS NULL'
            )
        )
        op.alter_column(
            table_name,
            column_name,
            existing_type=timestamp_type,
            nullable=False,
        )


def downgrade() -> None:
    timestamp_type = sa.DateTime(timezone=True)
    for table_name, column_name in reversed(TIMESTAMP_COLUMNS):
        op.alter_column(
            table_name,
            column_name,
            existing_type=timestamp_type,
            nullable=True,
        )
