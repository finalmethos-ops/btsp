"""vendor integration foundation

Revision ID: 0016_vendor_integrations
Revises: 0015_po_transmissions
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016_vendor_integrations"
down_revision: str | None = "0015_po_transmissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendor_endpoints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "vendor_code",
            sa.String(64),
            sa.ForeignKey("catalog_vendors.vendor_code"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("transport", sa.String(32), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("external_vendor_id", sa.String(128)),
        sa.Column("connection_reference", sa.String(255)),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("updated_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("vendor_code", "name", name="uq_vendor_endpoint_vendor_name"),
    )
    for column in ("vendor_code", "transport", "direction", "is_active"):
        op.create_index(f"ix_vendor_endpoints_{column}", "vendor_endpoints", [column])

    op.create_table(
        "vendor_inbound_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "endpoint_id",
            sa.String(36),
            sa.ForeignKey("vendor_endpoints.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("vendor_code", sa.String(64), nullable=False),
        sa.Column("external_event_id", sa.String(160), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("received_by", sa.String(320), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.String(1000)),
        sa.UniqueConstraint(
            "endpoint_id",
            "external_event_id",
            name="uq_vendor_inbound_event_endpoint_external",
        ),
    )
    for column in ("endpoint_id", "vendor_code", "event_type", "payload_sha256", "status"):
        op.create_index(f"ix_vendor_inbound_events_{column}", "vendor_inbound_events", [column])


def downgrade() -> None:
    op.drop_table("vendor_inbound_events")
    op.drop_table("vendor_endpoints")
