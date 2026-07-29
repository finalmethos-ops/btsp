"""invoice PDF intake

Revision ID: 0040_invoice_intake
Revises: 0039_po_attention
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0040_invoice_intake"
down_revision: str | None = "0039_po_attention"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoice_intake_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False, unique=True),
        sa.Column("sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(160), nullable=True),
        sa.Column("detected_vendor_code", sa.String(64), nullable=True),
        sa.Column("detected_store_number", sa.String(32), nullable=True),
        sa.Column("detected_po_number", sa.String(64), nullable=True),
        sa.Column(
            "suggested_purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("uploaded_by", sa.String(320), nullable=False),
        sa.Column("uploader_vendor_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in (
        "sha256",
        "invoice_number",
        "detected_vendor_code",
        "detected_store_number",
        "detected_po_number",
        "suggested_purchase_order_id",
        "status",
        "uploaded_by",
        "uploader_vendor_code",
    ):
        op.create_index(
            f"ix_invoice_intake_documents_{column}",
            "invoice_intake_documents",
            [column],
        )


def downgrade() -> None:
    op.drop_table("invoice_intake_documents")
