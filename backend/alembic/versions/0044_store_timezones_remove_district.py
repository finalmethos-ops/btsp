"""populate store timezones and remove district

Revision ID: 0044_store_timezones
Revises: 0043_vendor_directory
"""

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision: str = "0044_store_timezones"
down_revision: str | None = "0043_vendor_directory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    mapping_path = Path(__file__).resolve().parents[2] / "app" / "data" / "store_timezones.json"
    timezones: dict[str, str] = json.loads(mapping_path.read_text(encoding="utf-8"))
    stores = sa.table(
        "stores",
        sa.column("store_number", sa.String),
        sa.column("timezone", sa.String),
    )
    connection = op.get_bind()
    for store_number, timezone in timezones.items():
        connection.execute(
            stores.update().where(stores.c.store_number == store_number).values(timezone=timezone)
        )
    op.drop_column("stores", "district_code")


def downgrade() -> None:
    op.add_column("stores", sa.Column("district_code", sa.String(length=64), nullable=True))
