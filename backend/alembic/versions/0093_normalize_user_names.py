"""Normalize imported user display names."""

from alembic import op

revision = "0093_normalize_user_names"
down_revision = "0092_event_vendor_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET display_name = initcap(lower(trim(display_name)))")


def downgrade() -> None:
    pass
