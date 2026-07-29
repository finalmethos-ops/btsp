from io import BytesIO

import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import Base
from app.models.catalog import CatalogVendor
from app.services.invoice_intake_service import InvoiceIntakeError, ingest_invoice_pdfs, split_pdf


def _pdf(*pages: str) -> bytes:
    stream = BytesIO()
    document = canvas.Canvas(stream)
    for text in pages:
        document.drawString(72, 720, text)
        document.showPage()
    document.save()
    return stream.getvalue()


def test_invoice_batch_size_is_bounded(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.services.invoice_intake_service.MAX_BATCH_BYTES", 4)
    monkeypatch.setattr(settings, "invoice_intake_storage_path", str(tmp_path))
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db, pytest.raises(InvoiceIntakeError, match="batch"):
        ingest_invoice_pdfs(db, [("invoice.pdf", b"12345")], "actor@example.com", None)


def test_pdf_batch_separates_unique_invoices_and_extracts_hints(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "invoice_intake_storage_path", str(tmp_path))
    content = _pdf(
        "Invoice Number: INV-100 Vendor V-PDF Store # 100 PO-100-2026-07-001",
        "Invoice Number: INV-200 Vendor V-PDF Store # 200 PO-200-2026-07-002",
    )
    separated = split_pdf(content)
    assert [item.invoice_number for item in separated] == ["INV-100", "INV-200"]

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            CatalogVendor(
                vendor_code="V-PDF",
                name="PDF Vendor",
                is_active=True,
                source_file="test.xlsx",
            )
        )
        db.commit()

        documents, duplicates = ingest_invoice_pdfs(
            db,
            [("batch.pdf", content)],
            "vendor@example.com",
            "V-PDF",
        )

        assert duplicates == 0
        assert [item.invoice_number for item in documents] == ["INV-100", "INV-200"]
        assert [item.detected_store_number for item in documents] == ["100", "200"]
        assert [item.detected_po_number for item in documents] == [
            "PO-100-2026-07-001",
            "PO-200-2026-07-002",
        ]
        assert all((tmp_path / item.stored_filename).is_file() for item in documents)

        repeated, duplicates = ingest_invoice_pdfs(
            db,
            [("batch.pdf", content)],
            "vendor@example.com",
            "V-PDF",
        )
        assert repeated == []
        assert duplicates == 2


def test_multipage_invoice_continuations_stay_together() -> None:
    content = _pdf(
        "Invoice Number: INV-100 Page 1 of 3",
        "Invoice INV-999 referenced in notes — Page 2 of 3 Continued",
        "Line-item continuation Page 3 of 3",
        "Invoice Number: INV-200 Page 1 of 1",
    )

    separated = split_pdf(content)

    assert [(item.invoice_number, item.page_start, item.page_end) for item in separated] == [
        ("INV-100", 1, 3),
        ("INV-200", 4, 4),
    ]
