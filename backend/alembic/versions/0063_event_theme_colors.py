"""add event theme colors

Revision ID: 0063_event_theme_colors
Revises: 0062_event_vendor_booths
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0063_event_theme_colors"
down_revision: str | None = "0062_event_vendor_booths"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "managed_events",
        sa.Column(
            "theme_primary_color",
            sa.String(7),
            nullable=False,
            server_default="#07142c",
        ),
    )
    op.add_column(
        "managed_events",
        sa.Column(
            "theme_accent_color",
            sa.String(7),
            nullable=False,
            server_default="#ffd400",
        ),
    )


def downgrade() -> None:
    op.drop_column("managed_events", "theme_accent_color")
    op.drop_column("managed_events", "theme_primary_color")
