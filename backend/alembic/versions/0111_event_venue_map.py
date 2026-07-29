"""Add visual venue maps to managed events."""

import sqlalchemy as sa

from alembic import op

revision = "0111_event_venue_map"
down_revision = "0110_config_change_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_venue_map_assets",
        sa.Column(
            "event_id",
            sa.String(length=36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by", sa.String(length=320), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("event_venue_map_assets")
