"""connector import runs

Revision ID: 0019_connector_imports
Revises: 0018_shipments_asns
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_connector_imports"
down_revision: str | None = "0018_shipments_asns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vendor_connector_import_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "endpoint_id",
            sa.String(36),
            sa.ForeignKey("vendor_endpoints.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(160)),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(1000)),
        sa.Column("imported_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("endpoint_id", "content_sha256", name="uq_vendor_import_checksum"),
    )
    op.create_index("ix_vendor_import_endpoint", "vendor_connector_import_runs", ["endpoint_id"])
    op.create_index("ix_vendor_import_checksum", "vendor_connector_import_runs", ["content_sha256"])
    op.create_index("ix_vendor_import_status", "vendor_connector_import_runs", ["status"])
    op.add_column("vendor_inbound_events", sa.Column("import_run_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_vendor_event_import_run",
        "vendor_inbound_events",
        "vendor_connector_import_runs",
        ["import_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_vendor_event_import_run", "vendor_inbound_events", ["import_run_id"])


def downgrade() -> None:
    op.drop_index("ix_vendor_event_import_run", table_name="vendor_inbound_events")
    op.drop_constraint("fk_vendor_event_import_run", "vendor_inbound_events", type_="foreignkey")
    op.drop_column("vendor_inbound_events", "import_run_id")
    op.drop_table("vendor_connector_import_runs")
