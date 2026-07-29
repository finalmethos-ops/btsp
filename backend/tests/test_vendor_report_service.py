from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models import purchasing as _purchasing_models  # noqa: F401
from app.models import store as _store_models  # noqa: F401
from app.models import workflow as _workflow_models  # noqa: F401
from app.models.catalog import CatalogProduct, CatalogVendor
from app.models.invoice_intake import InvoiceIntakeDocument
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.services.vendor_report_service import build_vendor_report


def test_vendor_report_is_year_and_vendor_scoped() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                CatalogVendor(
                    vendor_code="V-REPORT",
                    name="Reporting Vendor",
                    is_active=True,
                    source_file="test.xlsx",
                ),
                CatalogVendor(
                    vendor_code="V-OTHER",
                    name="Other Vendor",
                    is_active=True,
                    source_file="test.xlsx",
                ),
            ]
        )
        db.add(
            CatalogProduct(
                product_code="REPORT-1",
                vendor_code="V-REPORT",
                name="Reporting Model",
                department="ELECTRONICS",
                product_category_code="TV",
                unit_price=Decimal("100.00"),
                currency="USD",
                minimum_order_quantity=1,
                is_available=True,
                is_active=True,
                source_file="test.xlsx",
            )
        )
        order = PurchaseOrder(
            po_number="PO-100-2026-01-001",
            workflow_code="VENDOR_ORDER",
            vendor_code="V-REPORT",
            status="active",
            currency="USD",
            subtotal=Decimal("200.00"),
            freight_total=0,
            tax_total=0,
            total=Decimal("200.00"),
            created_by="buyer@example.com",
            created_at=datetime(2026, 1, 15, tzinfo=UTC),
        )
        order.lines.append(
            PurchaseOrderLine(
                source_request_id="request-1",
                source_line_id=None,
                store_number="100",
                product_code="REPORT-1",
                product_name="Reporting Model",
                quantity=2,
                received_quantity=1,
                unit_price=Decimal("100.00"),
                freight_amount=0,
                tax_amount=0,
                extended_amount=Decimal("200.00"),
            )
        )
        db.add(order)
        db.add(
            InvoiceIntakeDocument(
                original_filename="invoice.pdf",
                stored_filename="invoice.pdf",
                sha256="a" * 64,
                page_start=1,
                page_end=1,
                detected_vendor_code="V-REPORT",
                extracted_text="",
                status="unreconciled",
                uploaded_by="vendor@example.com",
                uploader_vendor_code="V-REPORT",
            )
        )
        db.commit()

        report = build_vendor_report(db, "V-REPORT", 2026)

        assert report.purchase_order_count == 1
        assert report.units_ordered == 2
        assert report.units_received == 1
        assert report.fill_rate == 50
        assert report.annual_spend[0].amount == 200
        assert report.monthly_spend[0].month == 1
        assert report.category_spend[0].department == "ELECTRONICS"
        assert report.category_spend[0].product_code == "TV"
        assert report.unreconciled_invoice_count == 1
