"""add store loadout foundation

Revision ID: 0065_store_loadout_foundation
Revises: 0064_vendor_hall_foundation
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0065_store_loadout_foundation"
down_revision: str | None = "0064_vendor_hall_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "store_loadout_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("loadout_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("default_loadout_zone", sa.String(255), nullable=True),
        sa.Column("venue_departure_notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(320), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("event_id", name="uq_store_loadout_event"),
    )
    op.create_index("ix_store_loadout_events_event_id", "store_loadout_events", ["event_id"])
    op.create_index("ix_store_loadout_events_status", "store_loadout_events", ["status"])

    op.create_table(
        "store_loadout_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "store_loadout_event_id",
            sa.String(36),
            sa.ForeignKey("store_loadout_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("store_number", sa.String(32), nullable=False),
        sa.Column("entity_code", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("pickup_priority", sa.Integer(), nullable=False),
        sa.Column("loadout_zone", sa.String(255), nullable=True),
        sa.Column("distance_miles", sa.Numeric(8, 2), nullable=True),
        sa.Column("estimated_drive_minutes", sa.Integer(), nullable=True),
        sa.Column("recommended_departure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_by", sa.String(320), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_by", sa.String(320), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by", sa.String(320), nullable=True),
        *timestamps(),
    )
    for name, columns in (
        ("ix_store_loadout_assignments_store_loadout_event_id", ["store_loadout_event_id"]),
        ("ix_store_loadout_assignments_event_id", ["event_id"]),
        ("ix_store_loadout_assignments_store_number", ["store_number"]),
        ("ix_store_loadout_assignments_entity_code", ["entity_code"]),
        ("ix_store_loadout_assignments_status", ["status"]),
        ("ix_store_loadout_assignments_pickup_priority", ["pickup_priority"]),
        ("ix_store_loadout_assignments_loadout_zone", ["loadout_zone"]),
    ):
        op.create_index(name, "store_loadout_assignments", columns)

    op.create_table(
        "store_loadout_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "assignment_id",
            sa.String(36),
            sa.ForeignKey("store_loadout_assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_hall_booth_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_booths.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "vendor_hall_inventory_item_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_inventory_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("vendor_code", sa.String(64), nullable=False),
        sa.Column("booth_number", sa.String(64), nullable=False),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("model_number", sa.String(128), nullable=True),
        sa.Column("serial_number", sa.String(128), nullable=True),
        sa.Column("quantity_assigned", sa.Integer(), nullable=False),
        sa.Column("quantity_found", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("damage_notes", sa.Text(), nullable=True),
        sa.Column("missing_notes", sa.Text(), nullable=True),
        *timestamps(),
    )
    for name, columns in (
        ("ix_store_loadout_items_assignment_id", ["assignment_id"]),
        ("ix_store_loadout_items_event_id", ["event_id"]),
        ("ix_store_loadout_items_vendor_hall_booth_id", ["vendor_hall_booth_id"]),
        ("ix_store_loadout_items_vendor_hall_inventory_item_id", ["vendor_hall_inventory_item_id"]),
        ("ix_store_loadout_items_vendor_code", ["vendor_code"]),
        ("ix_store_loadout_items_booth_number", ["booth_number"]),
        ("ix_store_loadout_items_model_number", ["model_number"]),
        ("ix_store_loadout_items_serial_number", ["serial_number"]),
        ("ix_store_loadout_items_condition", ["condition"]),
        ("ix_store_loadout_items_status", ["status"]),
    ):
        op.create_index(name, "store_loadout_items", columns)

    op.create_table(
        "store_loadout_item_checkins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "loadout_item_id",
            sa.String(36),
            sa.ForeignKey("store_loadout_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assignment_id",
            sa.String(36),
            sa.ForeignKey("store_loadout_assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("quantity_found", sa.Integer(), nullable=False),
        sa.Column("damage_notes", sa.Text(), nullable=True),
        sa.Column("missing_notes", sa.Text(), nullable=True),
        sa.Column("checked_by", sa.String(320), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_store_loadout_item_checkins_loadout_item_id",
        "store_loadout_item_checkins",
        ["loadout_item_id"],
    )
    op.create_index(
        "ix_store_loadout_item_checkins_assignment_id",
        "store_loadout_item_checkins",
        ["assignment_id"],
    )
    op.create_index(
        "ix_store_loadout_item_checkins_status",
        "store_loadout_item_checkins",
        ["status"],
    )

    op.create_table(
        "store_loadout_signoffs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "assignment_id",
            sa.String(36),
            sa.ForeignKey("store_loadout_assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("signer_name", sa.String(255), nullable=False),
        sa.Column("signer_email", sa.String(320), nullable=False),
        sa.Column("signature_text", sa.String(255), nullable=False),
        sa.Column("exception_summary", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_store_loadout_signoffs_assignment_id",
        "store_loadout_signoffs",
        ["assignment_id"],
    )

    op.create_table(
        "store_loadout_audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "store_loadout_event_id",
            sa.String(36),
            sa.ForeignKey("store_loadout_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assignment_id",
            sa.String(36),
            sa.ForeignKey("store_loadout_assignments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "loadout_item_id",
            sa.String(36),
            sa.ForeignKey("store_loadout_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for name, columns in (
        ("ix_store_loadout_audit_log_event_id", ["event_id"]),
        ("ix_store_loadout_audit_log_store_loadout_event_id", ["store_loadout_event_id"]),
        ("ix_store_loadout_audit_log_assignment_id", ["assignment_id"]),
        ("ix_store_loadout_audit_log_loadout_item_id", ["loadout_item_id"]),
        ("ix_store_loadout_audit_log_action", ["action"]),
    ):
        op.create_index(name, "store_loadout_audit_log", columns)


def downgrade() -> None:
    for table in (
        "store_loadout_audit_log",
        "store_loadout_signoffs",
        "store_loadout_item_checkins",
        "store_loadout_items",
        "store_loadout_assignments",
        "store_loadout_events",
    ):
        op.drop_table(table)
