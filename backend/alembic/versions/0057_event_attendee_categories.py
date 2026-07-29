"""replace legacy attendee category

Revision ID: 0057_event_attendee_categories
Revises: 0056_event_attendance
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0057_event_attendee_categories"
down_revision: str | None = "0056_event_attendance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE event_memberships SET membership_type = "
        "'franchise_representative' WHERE membership_type = 'attendee'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE event_memberships SET membership_type = "
        "'attendee' WHERE membership_type = 'franchise_representative'"
    )
