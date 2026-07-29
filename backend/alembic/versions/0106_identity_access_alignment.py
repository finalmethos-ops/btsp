"""Remove a redundant vendor-access index already covered by the key."""

from alembic import op

revision = "0106_identity_access"
down_revision = "0105_vendor_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_user_vendor_access_vendor_code")


def downgrade() -> None:
    op.create_index(
        "ix_user_vendor_access_vendor_code",
        "user_vendor_access",
        ["vendor_code"],
    )
