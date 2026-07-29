"""add event management foundation

Revision ID: 0049_event_management
Revises: 0048_model_identifiers
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0049_event_management"
down_revision: str | None = "0048_model_identifiers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "managed_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(96), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("venue_name", sa.String(255), nullable=False),
        sa.Column("address_line1", sa.String(255), nullable=False),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(128), nullable=False),
        sa.Column("state_code", sa.String(32), nullable=False),
        sa.Column("postal_code", sa.String(24), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_managed_events_slug", "managed_events", ["slug"], unique=True)
    op.create_index("ix_managed_events_status", "managed_events", ["status"])
    op.create_index("ix_managed_events_starts_at", "managed_events", ["starts_at"])
    op.create_index("ix_managed_events_ends_at", "managed_events", ["ends_at"])
    op.create_table(
        "event_branding_assets",
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by", sa.String(320), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "managed_sub_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("module_codes", sa.JSON(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_managed_sub_events_event_id", "managed_sub_events", ["event_id"])
    op.create_index("ix_managed_sub_events_starts_at", "managed_sub_events", ["starts_at"])
    op.create_table(
        "event_memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("membership_type", sa.String(24), nullable=False),
        sa.Column(
            "vendor_code",
            sa.String(64),
            sa.ForeignKey("catalog_vendors.vendor_code", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("module_codes", sa.JSON(), nullable=False),
        sa.Column("task_scope", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_membership_user"),
    )
    op.create_index("ix_event_memberships_event_id", "event_memberships", ["event_id"])
    op.create_index("ix_event_memberships_user_id", "event_memberships", ["user_id"])
    op.create_index(
        "ix_event_memberships_membership_type",
        "event_memberships",
        ["membership_type"],
    )
    op.create_index("ix_event_memberships_vendor_code", "event_memberships", ["vendor_code"])


def downgrade() -> None:
    op.drop_table("event_memberships")
    op.drop_table("managed_sub_events")
    op.drop_table("event_branding_assets")
    op.drop_table("managed_events")
