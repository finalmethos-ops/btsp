"""Add secure multi-vendor access assignments.

Revision ID: 0085_multi_vendor_user_access
Revises: 0084_event_filler_slides
"""

import sqlalchemy as sa

from alembic import op

revision = "0085_multi_vendor_user_access"
down_revision = "0084_event_filler_slides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_vendor_access",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "vendor_code",
            sa.String(length=64),
            sa.ForeignKey("catalog_vendors.vendor_code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", "vendor_code"),
    )
    op.create_index(
        "ix_user_vendor_access_vendor_code",
        "user_vendor_access",
        ["vendor_code"],
    )
    op.execute(
        """
        INSERT INTO user_vendor_access (user_id, vendor_code)
        SELECT users.id, users.vendor_code
        FROM users
        JOIN catalog_vendors
          ON catalog_vendors.vendor_code = users.vendor_code
        WHERE users.vendor_code IS NOT NULL
        ON CONFLICT (user_id, vendor_code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_vendor_access_vendor_code",
        table_name="user_vendor_access",
    )
    op.drop_table("user_vendor_access")
