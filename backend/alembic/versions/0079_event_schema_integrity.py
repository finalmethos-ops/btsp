"""Align event indexes and remove redundant slug uniqueness.

Revision ID: 0079_event_schema_integrity
Revises: 0078_vendor_hall_booth_visits
"""

from alembic import op

revision = "0079_event_schema_integrity"
down_revision = "0078_vendor_hall_booth_visits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_vendor_hall_saved_booths_vendor_hall_booth_id",
        "vendor_hall_saved_booths",
        ["vendor_hall_booth_id"],
    )
    op.drop_constraint("managed_events_slug_key", "managed_events", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("managed_events_slug_key", "managed_events", ["slug"])
    op.drop_index(
        "ix_vendor_hall_saved_booths_vendor_hall_booth_id",
        table_name="vendor_hall_saved_booths",
    )
