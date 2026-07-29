"""add vendor hall foundation

Revision ID: 0064_vendor_hall_foundation
Revises: 0063_event_theme_colors
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0064_vendor_hall_foundation"
down_revision: str | None = "0063_event_theme_colors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "vendor_hall_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sub_event_id",
            sa.String(36),
            sa.ForeignKey("managed_sub_events.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vendor_submission_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("staff_checkin_opens_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("staff_checkin_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allow_vendor_edits_after_submission", sa.Boolean(), nullable=False),
        sa.Column("require_staff_checkin", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("event_id", "sub_event_id", name="uq_vendor_hall_event"),
    )
    op.create_index("ix_vendor_hall_events_event_id", "vendor_hall_events", ["event_id"])
    op.create_index("ix_vendor_hall_events_sub_event_id", "vendor_hall_events", ["sub_event_id"])
    op.create_index("ix_vendor_hall_events_status", "vendor_hall_events", ["status"])

    op.create_table(
        "vendor_hall_booths",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "vendor_hall_event_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_vendor_booth_id",
            sa.String(36),
            sa.ForeignKey("event_vendor_booths.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_code",
            sa.String(64),
            sa.ForeignKey("catalog_vendors.vendor_code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("booth_number", sa.String(64), nullable=False),
        sa.Column("booth_name", sa.String(255), nullable=False),
        sa.Column("floor_map_zone", sa.String(255), nullable=True),
        sa.Column("map_x", sa.Numeric(10, 4), nullable=True),
        sa.Column("map_y", sa.Numeric(10, 4), nullable=True),
        sa.Column("map_width", sa.Numeric(10, 4), nullable=True),
        sa.Column("map_height", sa.Numeric(10, 4), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", sa.String(320), nullable=True),
        sa.Column("checkin_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checkin_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_in_by", sa.String(320), nullable=True),
        sa.Column("admin_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_reviewed_by", sa.String(320), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(320), nullable=True),
        *timestamps(),
        sa.UniqueConstraint(
            "event_id",
            "vendor_code",
            "booth_number",
            name="uq_vendor_hall_booth_identity",
        ),
    )
    for name, columns in (
        ("ix_vendor_hall_booths_vendor_hall_event_id", ["vendor_hall_event_id"]),
        ("ix_vendor_hall_booths_event_vendor_booth_id", ["event_vendor_booth_id"]),
        ("ix_vendor_hall_booths_event_id", ["event_id"]),
        ("ix_vendor_hall_booths_vendor_code", ["vendor_code"]),
        ("ix_vendor_hall_booths_booth_number", ["booth_number"]),
        ("ix_vendor_hall_booths_status", ["status"]),
    ):
        op.create_index(name, "vendor_hall_booths", columns)

    op.create_table(
        "vendor_hall_inventory_imports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "vendor_hall_booth_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.String(320), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_vendor_hall_inventory_imports_vendor_hall_booth_id",
        "vendor_hall_inventory_imports",
        ["vendor_hall_booth_id"],
    )
    op.create_index(
        "ix_vendor_hall_inventory_imports_status",
        "vendor_hall_inventory_imports",
        ["status"],
    )

    op.create_table(
        "vendor_hall_inventory_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "vendor_hall_booth_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("vendor_code", sa.String(64), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column(
            "source_import_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_inventory_imports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("model_number", sa.String(128), nullable=True),
        sa.Column("serial_number", sa.String(128), nullable=True),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity_expected", sa.Integer(), nullable=False),
        sa.Column("quantity_checked_in", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("condition", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("available_for_sale", sa.Boolean(), nullable=False),
        sa.Column("sell_to_buddys_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("vendor_notes", sa.Text(), nullable=True),
        sa.Column("staff_notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(320), nullable=False),
        *timestamps(),
    )
    for name, columns in (
        ("ix_vendor_hall_inventory_items_vendor_hall_booth_id", ["vendor_hall_booth_id"]),
        ("ix_vendor_hall_inventory_items_event_id", ["event_id"]),
        ("ix_vendor_hall_inventory_items_vendor_code", ["vendor_code"]),
        ("ix_vendor_hall_inventory_items_source", ["source"]),
        ("ix_vendor_hall_inventory_items_source_import_id", ["source_import_id"]),
        ("ix_vendor_hall_inventory_items_model_number", ["model_number"]),
        ("ix_vendor_hall_inventory_items_serial_number", ["serial_number"]),
        ("ix_vendor_hall_inventory_items_condition", ["condition"]),
        ("ix_vendor_hall_inventory_items_status", ["status"]),
        ("ix_vendor_hall_inventory_items_available_for_sale", ["available_for_sale"]),
    ):
        op.create_index(name, "vendor_hall_inventory_items", columns)

    op.create_table(
        "vendor_hall_item_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "inventory_item_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_inventory_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attachment_type", sa.String(32), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by", sa.String(320), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_vendor_hall_item_attachments_inventory_item_id",
        "vendor_hall_item_attachments",
        ["inventory_item_id"],
    )
    op.create_index(
        "ix_vendor_hall_item_attachments_attachment_type",
        "vendor_hall_item_attachments",
        ["attachment_type"],
    )

    op.create_table(
        "vendor_hall_item_checkins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "inventory_item_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_inventory_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_hall_booth_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("quantity_checked", sa.Integer(), nullable=False),
        sa.Column("condition", sa.String(32), nullable=True),
        sa.Column("damage_notes", sa.Text(), nullable=True),
        sa.Column("exception_notes", sa.Text(), nullable=True),
        sa.Column("checked_by", sa.String(320), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_vendor_hall_item_checkins_inventory_item_id",
        "vendor_hall_item_checkins",
        ["inventory_item_id"],
    )
    op.create_index(
        "ix_vendor_hall_item_checkins_vendor_hall_booth_id",
        "vendor_hall_item_checkins",
        ["vendor_hall_booth_id"],
    )
    op.create_index("ix_vendor_hall_item_checkins_status", "vendor_hall_item_checkins", ["status"])

    op.create_table(
        "vendor_hall_booth_checkins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "vendor_hall_booth_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_by", sa.String(320), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_by", sa.String(320), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("items_expected", sa.Integer(), nullable=False),
        sa.Column("items_checked", sa.Integer(), nullable=False),
        sa.Column("exceptions_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_vendor_hall_booth_checkins_vendor_hall_booth_id",
        "vendor_hall_booth_checkins",
        ["vendor_hall_booth_id"],
    )
    op.create_index(
        "ix_vendor_hall_booth_checkins_status",
        "vendor_hall_booth_checkins",
        ["status"],
    )

    op.create_table(
        "vendor_hall_exceptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "vendor_hall_booth_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "inventory_item_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_inventory_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("exception_type", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_by", sa.String(320), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
    )
    for name, columns in (
        ("ix_vendor_hall_exceptions_vendor_hall_booth_id", ["vendor_hall_booth_id"]),
        ("ix_vendor_hall_exceptions_inventory_item_id", ["inventory_item_id"]),
        ("ix_vendor_hall_exceptions_exception_type", ["exception_type"]),
        ("ix_vendor_hall_exceptions_severity", ["severity"]),
        ("ix_vendor_hall_exceptions_status", ["status"]),
    ):
        op.create_index(name, "vendor_hall_exceptions", columns)

    op.create_table(
        "vendor_hall_floor_maps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "vendor_hall_event_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("image_filename", sa.String(255), nullable=True),
        sa.Column("image_content_type", sa.String(128), nullable=True),
        sa.Column("image_content", sa.LargeBinary(), nullable=True),
        sa.Column("layout_json", sa.JSON(), nullable=False),
        sa.Column("uploaded_by", sa.String(320), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_vendor_hall_floor_maps_vendor_hall_event_id",
        "vendor_hall_floor_maps",
        ["vendor_hall_event_id"],
    )
    op.create_index("ix_vendor_hall_floor_maps_is_active", "vendor_hall_floor_maps", ["is_active"])

    op.create_table(
        "vendor_hall_audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_hall_event_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_hall_booth_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_booths.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "inventory_item_id",
            sa.String(36),
            sa.ForeignKey("vendor_hall_inventory_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for name, columns in (
        ("ix_vendor_hall_audit_log_event_id", ["event_id"]),
        ("ix_vendor_hall_audit_log_vendor_hall_event_id", ["vendor_hall_event_id"]),
        ("ix_vendor_hall_audit_log_vendor_hall_booth_id", ["vendor_hall_booth_id"]),
        ("ix_vendor_hall_audit_log_inventory_item_id", ["inventory_item_id"]),
        ("ix_vendor_hall_audit_log_action", ["action"]),
    ):
        op.create_index(name, "vendor_hall_audit_log", columns)


def downgrade() -> None:
    for table in (
        "vendor_hall_audit_log",
        "vendor_hall_floor_maps",
        "vendor_hall_exceptions",
        "vendor_hall_booth_checkins",
        "vendor_hall_item_checkins",
        "vendor_hall_item_attachments",
        "vendor_hall_inventory_items",
        "vendor_hall_inventory_imports",
        "vendor_hall_booths",
        "vendor_hall_events",
    ):
        op.drop_table(table)
