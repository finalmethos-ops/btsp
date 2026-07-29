"""Align catalog import timestamps with the required model metadata."""

import sqlalchemy as sa

from alembic import op

revision = "0101_catalog_import_timestamp"
down_revision = "0100_analytics_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "catalog_import_runs",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.alter_column(
        "catalog_import_runs",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
