"""add event product slide builder

Revision ID: 0050_event_product_slides
Revises: 0049_event_management
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0050_event_product_slides"
down_revision: str | None = "0049_event_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_product_slides",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(36),
            sa.ForeignKey("managed_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sub_event_id",
            sa.String(36),
            sa.ForeignKey("managed_sub_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "catalog_product_code",
            sa.String(64),
            sa.ForeignKey("catalog_products.product_code", ondelete="SET NULL", onupdate="CASCADE"),
            nullable=True,
        ),
        sa.Column("model_number", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "vendor_code",
            sa.String(64),
            sa.ForeignKey("catalog_vendors.vendor_code", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("specifications", sa.Text(), nullable=True),
        sa.Column("event_unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("suggested_retail", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("minimum_order_quantity", sa.Integer(), nullable=False),
        sa.Column("available_inventory", sa.Integer(), nullable=True),
        sa.Column("max_event_units", sa.Integer(), nullable=True),
        sa.Column("allow_waitlist", sa.Boolean(), nullable=False),
        sa.Column("delivery_window_start", sa.Date(), nullable=False),
        sa.Column("delivery_window_end", sa.Date(), nullable=False),
        sa.Column("vendor_delivery_notes", sa.Text(), nullable=True),
        sa.Column("presenter_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_by", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("sub_event_id", "position", name="uq_event_slide_position"),
    )
    for name, columns in (
        ("ix_event_product_slides_event_id", ["event_id"]),
        ("ix_event_product_slides_sub_event_id", ["sub_event_id"]),
        ("ix_event_product_slides_position", ["position"]),
        ("ix_event_product_slides_catalog_product_code", ["catalog_product_code"]),
        ("ix_event_product_slides_vendor_code", ["vendor_code"]),
        ("ix_event_product_slides_status", ["status"]),
    ):
        op.create_index(name, "event_product_slides", columns)
    op.create_table(
        "event_product_slide_images",
        sa.Column(
            "slide_id",
            sa.String(36),
            sa.ForeignKey("event_product_slides.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by", sa.String(320), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("event_product_slide_images")
    op.drop_table("event_product_slides")
