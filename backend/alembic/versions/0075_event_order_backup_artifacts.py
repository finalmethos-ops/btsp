"""Archive event order backups at settlement close.

Revision ID: 0075_event_backup_artifacts
Revises: 0074_event_release_requests
"""

import sqlalchemy as sa

from alembic import op

revision = "0075_event_backup_artifacts"
down_revision = "0074_event_release_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_order_backup_artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(length=36),
            sa.ForeignKey("managed_events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=160), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("event_id", name="uq_event_order_backup_artifact_event"),
    )
    op.create_index(
        "ix_event_order_backup_artifacts_event_id",
        "event_order_backup_artifacts",
        ["event_id"],
    )
    op.create_index(
        "ix_event_order_backup_artifacts_sha256",
        "event_order_backup_artifacts",
        ["sha256"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_order_backup_artifacts_sha256",
        table_name="event_order_backup_artifacts",
    )
    op.drop_index(
        "ix_event_order_backup_artifacts_event_id",
        table_name="event_order_backup_artifacts",
    )
    op.drop_table("event_order_backup_artifacts")
