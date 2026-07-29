"""Link vendor hall booths to staff inspection tasks."""

import sqlalchemy as sa

from alembic import op

revision = "0094_vendor_hall_staff_tasks"
down_revision = "0093_normalize_user_names"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vendor_hall_booths",
        sa.Column("assigned_staff_membership_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_vendor_hall_booths_assigned_staff_membership_id",
        "vendor_hall_booths",
        ["assigned_staff_membership_id"],
    )
    op.create_foreign_key(
        "fk_vendor_hall_booths_assigned_staff_membership",
        "vendor_hall_booths",
        "event_memberships",
        ["assigned_staff_membership_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "event_staff_tasks",
        sa.Column("vendor_hall_booth_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_event_staff_tasks_vendor_hall_booth_id",
        "event_staff_tasks",
        ["vendor_hall_booth_id"],
    )
    op.create_foreign_key(
        "fk_event_staff_tasks_vendor_hall_booth",
        "event_staff_tasks",
        "vendor_hall_booths",
        ["vendor_hall_booth_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_event_staff_tasks_vendor_hall_booth", "event_staff_tasks", type_="foreignkey"
    )
    op.drop_index("ix_event_staff_tasks_vendor_hall_booth_id", table_name="event_staff_tasks")
    op.drop_column("event_staff_tasks", "vendor_hall_booth_id")
    op.drop_constraint(
        "fk_vendor_hall_booths_assigned_staff_membership", "vendor_hall_booths", type_="foreignkey"
    )
    op.drop_index(
        "ix_vendor_hall_booths_assigned_staff_membership_id", table_name="vendor_hall_booths"
    )
    op.drop_column("vendor_hall_booths", "assigned_staff_membership_id")
