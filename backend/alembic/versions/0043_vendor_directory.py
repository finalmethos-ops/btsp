"""replace the active vendor directory

Revision ID: 0043_vendor_directory
Revises: 0042_remove_category
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0043_vendor_directory"
down_revision: str | None = "0042_remove_category"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VENDORS = (
    ("AFFORDABLE-FURNITURE", "AFFORDABLE FURNITURE"),
    ("ALBANY-INDUSTRIES", "ALBANY INDUSTRIES LLC"),
    ("AMERICAN-WHOLESALE-FURNITURE", "AMERICAN WHOLESALE FURNITURE"),
    ("ASHLEY-FURNITURE", "ASHLEY FURNITURE"),
    ("BELLONA-USA", "BELLONA USA"),
    ("C-L-SUPPLY", "C&L SUPPLY"),
    ("CLASSY-ART", "CLASSY ART"),
    ("CLIMATIC", "CLIMATIC"),
    ("COASTER", "COASTER"),
    ("CORSICANA", "CORSICANA"),
    ("CROWN-MARK", "CROWN MARK"),
    ("D-H-DISTRIBUTING", "D&H DISTRIBUTING"),
    ("D-W-SILKS", "D&W SILKS, INC"),
    ("DALYN-RUG-COMPANY", "DALYN RUG COMPANY"),
    ("DONCO", "DONCO"),
    ("ELEMENTS-INTERNATIONAL-GROUP", "ELEMENTS INTERNATIONAL GROUP"),
    ("EMERALD-HOME-FURNISHINGS", "EMERALD HOME FURNISHINGS"),
    ("FLORIDA-STATE-GAMES", "FLORIDA STATE GAMES"),
    ("GE-APPLIANCES", "GE APPLIANCES"),
    ("GLOBAL-FURNITURE-USA", "GLOBAL FURNITURE USA"),
    ("HOLLYWOOD-BED-SPRING", "HOLLYWOOD BED & SPRING CO., INC"),
    ("HOMESTRETCH-FURNITURE", "HOMESTRETCH FURNITURE"),
    ("HUGHES-FURNITURE-INDUSTRIES", "HUGHES FURNITURE INDUSTRIES"),
    ("KODIAK-FURNITURE", "KODIAK FURNITURE"),
    ("L2", "L2"),
    ("LEOPARD-MOBILITY", "LEOPARD MOBILITY"),
    ("LIVING-ESSENTIALS", "LIVING ESSENTIALS"),
    ("NAVAIR-CORPORATION", "NAVAIR CORPORATION"),
    ("NEKTOVA", "NEKTOVA"),
    ("NEOLIVING", "NEOLIVING"),
    ("NEW-CLASSIC-HOME-FURNISHINGS", "NEW CLASSIC HOME FURNISHINGS"),
    ("OFFICE-STAR-PRODUCTS", "OFFICE STAR PRODUCTS"),
    ("OROURKE-SALES-COMPANY", "O'ROURKE SALES COMPANY"),
    ("SEALY-MATTRESS", "SEALY MATTRESS"),
    ("SHERWOOD-BEDDING", "SHERWOOD BEDDING"),
    ("SIMPLY-BUNKBEDS", "SIMPLY BUNKBEDS"),
    ("SOUTHERLAND", "SOUTHERLAND INC"),
    ("STEVE-SILVER-COMPANY", "STEVE SILVER COMPANY"),
    ("TECHNICAL-PRO", "TECHNICAL PRO"),
    ("W-SILVER-PRODUCTS", "W. SILVER PRODUCTS"),
)


def upgrade() -> None:
    connection = op.get_bind()
    vendors = sa.table(
        "catalog_vendors",
        sa.column("vendor_code", sa.String),
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("source_file", sa.String),
    )
    connection.execute(vendors.update().values(is_active=False))
    for vendor_code, name in VENDORS:
        existing = connection.execute(
            sa.select(vendors.c.vendor_code).where(vendors.c.vendor_code == vendor_code)
        ).first()
        values = {
            "name": name,
            "is_active": True,
            "source_file": "VEndor Listing.xlsx",
        }
        if existing:
            connection.execute(
                vendors.update().where(vendors.c.vendor_code == vendor_code).values(**values)
            )
        else:
            connection.execute(vendors.insert().values(vendor_code=vendor_code, **values))


def downgrade() -> None:
    connection = op.get_bind()
    vendors = sa.table(
        "catalog_vendors",
        sa.column("vendor_code", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    codes = [vendor_code for vendor_code, _name in VENDORS]
    connection.execute(
        vendors.update().where(vendors.c.vendor_code.in_(codes)).values(is_active=False)
    )
