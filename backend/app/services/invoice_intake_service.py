import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader, PdfWriter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import purchasing as _purchasing_models  # noqa: F401
from app.models import store as _store_models  # noqa: F401
from app.models import workflow as _workflow_models  # noqa: F401
from app.models.catalog import CatalogVendor
from app.models.invoice_intake import InvoiceIntakeDocument
from app.models.purchase_order import PurchaseOrder, PurchaseOrderSource

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_BATCH_BYTES = 10 * 1024 * 1024
MAX_BATCH_FILES = 25
MAX_PDF_PAGES = 250
INVOICE_PATTERN = re.compile(
    r"\binvoice\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9_-]{2,})",
    re.IGNORECASE,
)
PO_PATTERN = re.compile(r"\bPO-[A-Z0-9]+-\d{4}-\d{2}-\d{3}\b", re.IGNORECASE)
STORE_PATTERN = re.compile(
    r"\bstore\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9-]{2,32})",
    re.IGNORECASE,
)
CONTINUATION_PATTERN = re.compile(
    r"\b(?:continued|continuation)\b|\bpage\s*(?:number\s*)?[:#-]?\s*([2-9]\d*)\b",
    re.IGNORECASE,
)


class InvoiceIntakeError(ValueError):
    pass


@dataclass
class ParsedInvoice:
    content: bytes
    page_start: int
    page_end: int
    text: str
    invoice_number: str | None


def _invoice_number(text: str) -> str | None:
    match = INVOICE_PATTERN.search(text)
    return match.group(1).upper() if match else None


def _header_invoice_number(text: str) -> str | None:
    # Invoice identity normally appears in the header. Limiting the scan avoids
    # treating invoice references in line-item notes or remittance text as a new document.
    header_lines = text.splitlines()[:15]
    return _invoice_number("\n".join(header_lines)[:1500])


def _is_continuation_page(text: str) -> bool:
    return CONTINUATION_PATTERN.search(text[:2000]) is not None


def split_pdf(content: bytes) -> list[ParsedInvoice]:
    if not content.startswith(b"%PDF-"):
        raise InvoiceIntakeError("Invoice files must be valid PDFs")
    try:
        reader = PdfReader(BytesIO(content))
    except Exception as exc:
        raise InvoiceIntakeError("Invoice PDF could not be read") from exc
    if reader.is_encrypted:
        raise InvoiceIntakeError("Password-protected invoice PDFs are not supported")
    if not reader.pages:
        raise InvoiceIntakeError("Invoice PDF contains no pages")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise InvoiceIntakeError(f"Invoice PDF must not exceed {MAX_PDF_PAGES} pages")
    page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
    groups: list[tuple[int, int, str | None]] = []
    start = 0
    current_number = _header_invoice_number(page_texts[0])
    for index, text in enumerate(page_texts[1:], start=1):
        detected = _header_invoice_number(text)
        if _is_continuation_page(text):
            if current_number is None and detected:
                current_number = detected
            continue
        if detected and current_number is not None and detected != current_number:
            groups.append((start, index - 1, current_number))
            start = index
            current_number = detected
        elif current_number is None and detected:
            current_number = detected
    groups.append((start, len(page_texts) - 1, current_number))
    parsed: list[ParsedInvoice] = []
    for start, end, number in groups:
        writer = PdfWriter()
        for page_index in range(start, end + 1):
            writer.add_page(reader.pages[page_index])
        stream = BytesIO()
        writer.write(stream)
        parsed.append(
            ParsedInvoice(
                content=stream.getvalue(),
                page_start=start + 1,
                page_end=end + 1,
                text="\n".join(page_texts[start : end + 1]),
                invoice_number=number,
            )
        )
    return parsed


def _detect_vendor(db: Session, text: str, uploader_vendor_code: str | None) -> str | None:
    if uploader_vendor_code:
        return uploader_vendor_code
    upper = text.upper()
    vendors = db.scalars(select(CatalogVendor).where(CatalogVendor.is_active.is_(True))).all()
    for vendor in vendors:
        if re.search(rf"\b{re.escape(vendor.vendor_code.upper())}\b", upper):
            return vendor.vendor_code
    for vendor in vendors:
        if len(vendor.name) >= 4 and vendor.name.upper() in upper:
            return vendor.vendor_code
    return None


def _suggest_order(
    db: Session,
    po_number: str | None,
    vendor_code: str | None,
    store_number: str | None,
) -> PurchaseOrder | None:
    if po_number:
        order = db.scalar(select(PurchaseOrder).where(PurchaseOrder.po_number == po_number.upper()))
        if order is not None and (vendor_code is None or order.vendor_code == vendor_code):
            return order
    statement = (
        select(PurchaseOrder)
        .join(PurchaseOrderSource)
        .where(PurchaseOrder.status.not_in({"cancelled", "vendor_rejected"}))
        .order_by(PurchaseOrder.created_at.desc())
    )
    if vendor_code:
        statement = statement.where(PurchaseOrder.vendor_code == vendor_code)
    if store_number:
        statement = statement.where(PurchaseOrderSource.store_number == store_number)
    if vendor_code or store_number:
        return db.scalar(statement.limit(1))
    return None


def ingest_invoice_pdfs(
    db: Session,
    files: list[tuple[str, bytes]],
    actor: str,
    uploader_vendor_code: str | None,
) -> tuple[list[InvoiceIntakeDocument], int]:
    if not files or len(files) > MAX_BATCH_FILES:
        raise InvoiceIntakeError(f"Upload between 1 and {MAX_BATCH_FILES} PDF files")
    if sum(len(content) for _, content in files) > MAX_BATCH_BYTES:
        raise InvoiceIntakeError(f"Invoice upload batch must not exceed {MAX_BATCH_BYTES} bytes")
    storage = Path(settings.invoice_intake_storage_path)
    storage.mkdir(parents=True, exist_ok=True)
    created: list[InvoiceIntakeDocument] = []
    duplicates = 0
    for original_filename, content in files:
        if (
            not original_filename.lower().endswith(".pdf")
            or not content
            or len(content) > MAX_PDF_BYTES
        ):
            raise InvoiceIntakeError("Each upload must be a non-empty PDF no larger than 20 MB")
        for parsed in split_pdf(content):
            digest = hashlib.sha256(parsed.content).hexdigest()
            existing = db.scalar(
                select(InvoiceIntakeDocument).where(InvoiceIntakeDocument.sha256 == digest)
            )
            if existing:
                duplicates += 1
                continue
            po_match = PO_PATTERN.search(parsed.text)
            po_number = po_match.group(0).upper() if po_match else None
            store_match = STORE_PATTERN.search(parsed.text)
            store_number = store_match.group(1).upper() if store_match else None
            if po_number:
                store_number = po_number.split("-")[1]
            vendor_code = _detect_vendor(db, parsed.text, uploader_vendor_code)
            suggested = _suggest_order(db, po_number, vendor_code, store_number)
            stored_filename = f"{uuid4()}.pdf"
            (storage / stored_filename).write_bytes(parsed.content)
            document = InvoiceIntakeDocument(
                original_filename=original_filename,
                stored_filename=stored_filename,
                sha256=digest,
                page_start=parsed.page_start,
                page_end=parsed.page_end,
                invoice_number=parsed.invoice_number,
                detected_vendor_code=vendor_code,
                detected_store_number=store_number,
                detected_po_number=po_number,
                suggested_purchase_order_id=suggested.id if suggested else None,
                extracted_text=parsed.text[:100_000],
                status="unreconciled",
                uploaded_by=actor,
                uploader_vendor_code=uploader_vendor_code,
            )
            db.add(document)
            created.append(document)
    db.commit()
    for document in created:
        db.refresh(document)
    return created, duplicates


def list_unreconciled_documents(
    db: Session, vendor_code: str | None
) -> list[tuple[InvoiceIntakeDocument, str | None]]:
    statement = (
        select(InvoiceIntakeDocument, PurchaseOrder.po_number)
        .outerjoin(
            PurchaseOrder,
            PurchaseOrder.id == InvoiceIntakeDocument.suggested_purchase_order_id,
        )
        .where(InvoiceIntakeDocument.status.in_({"unreconciled", "paired"}))
        .order_by(InvoiceIntakeDocument.created_at.desc())
    )
    if vendor_code:
        statement = statement.where(InvoiceIntakeDocument.detected_vendor_code == vendor_code)
    return list(db.execute(statement).all())


def document_path(document: InvoiceIntakeDocument) -> Path:
    path = Path(settings.invoice_intake_storage_path) / document.stored_filename
    if not path.is_file():
        raise InvoiceIntakeError("Stored invoice PDF is unavailable")
    return path
