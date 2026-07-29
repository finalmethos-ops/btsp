"""Add photo evidence for store loadout items."""

import sqlalchemy as sa

from alembic import op

revision = "0099_loadout_item_attachments"
down_revision = "0098_loadout_vehicle_statuses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_loadout_item_attachments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("assignment_id", sa.String(length=36), nullable=False),
        sa.Column("loadout_item_id", sa.String(length=36), nullable=False),
        sa.Column("attachment_type", sa.String(length=32), nullable=False, server_default="photo"),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["event_id"], ["managed_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["store_loadout_assignments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["loadout_item_id"], ["store_loadout_items.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_store_loadout_item_attachments_event_id", "store_loadout_item_attachments", ["event_id"]
    )
    op.create_index(
        "ix_store_loadout_item_attachments_assignment_id",
        "store_loadout_item_attachments",
        ["assignment_id"],
    )
    op.create_index(
        "ix_store_loadout_item_attachments_loadout_item_id",
        "store_loadout_item_attachments",
        ["loadout_item_id"],
    )
    op.create_index(
        "ix_store_loadout_item_attachments_attachment_type",
        "store_loadout_item_attachments",
        ["attachment_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_store_loadout_item_attachments_attachment_type",
        table_name="store_loadout_item_attachments",
    )
    op.drop_index(
        "ix_store_loadout_item_attachments_loadout_item_id",
        table_name="store_loadout_item_attachments",
    )
    op.drop_index(
        "ix_store_loadout_item_attachments_assignment_id",
        table_name="store_loadout_item_attachments",
    )
    op.drop_index(
        "ix_store_loadout_item_attachments_event_id", table_name="store_loadout_item_attachments"
    )
    op.drop_table("store_loadout_item_attachments")
