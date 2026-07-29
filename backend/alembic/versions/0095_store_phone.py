"""Add store contact phone for loadout manifests."""

import sqlalchemy as sa

from alembic import op

revision = "0095_store_phone"
down_revision = "0094_vendor_hall_staff_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stores", sa.Column("phone", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("stores", "phone")
