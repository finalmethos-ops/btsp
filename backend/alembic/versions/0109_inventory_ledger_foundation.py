"""Add durable inventory ledger, reservation, and transfer records."""

import sqlalchemy as sa

from alembic import op

revision = "0109_inventory_ledger"
down_revision = "0108_auth_session_security"
branch_labels = None
depends_on = None


def _common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 0), nullable=False),
        sa.Column("created_by", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "inventory_ledger_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column("store_number", sa.String(length=32), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(14, 0), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("reference_type", sa.String(length=64), nullable=True),
        sa.Column("reference_id", sa.String(length=128), nullable=True),
        sa.Column("actor", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["store_number"], ["stores.store_number"], ondelete="RESTRICT"),
    )
    op.create_table(
        "inventory_reservations",
        *_common_columns(),
        sa.Column("store_number", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["store_number"], ["stores.store_number"], ondelete="RESTRICT"),
    )
    op.create_table(
        "inventory_transfers",
        *_common_columns(),
        sa.Column("from_store_number", sa.String(length=32), nullable=False),
        sa.Column("to_store_number", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="posted"),
        sa.ForeignKeyConstraint(
            ["from_store_number"], ["stores.store_number"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["to_store_number"], ["stores.store_number"], ondelete="RESTRICT"),
    )
    for table, columns in (
        ("inventory_ledger_entries", ("product_code", "store_number", "reason")),
        ("inventory_reservations", ("product_code", "store_number", "status")),
        ("inventory_transfers", ("product_code", "from_store_number", "to_store_number", "status")),
    ):
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade() -> None:
    op.drop_table("inventory_transfers")
    op.drop_table("inventory_reservations")
    op.drop_table("inventory_ledger_entries")
