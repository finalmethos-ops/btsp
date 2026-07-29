from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.identity import User
from app.models.invoice_intake import InvoiceIntakeDocument
from app.schemas.invoice_intake import InvoiceIntakeBatchResponse, InvoiceIntakeResponse
from app.services.invoice_intake_service import (
    MAX_BATCH_BYTES,
    MAX_BATCH_FILES,
    MAX_PDF_BYTES,
    InvoiceIntakeError,
    document_path,
    ingest_invoice_pdfs,
    list_unreconciled_documents,
)

router = APIRouter(prefix="/invoice-intake", tags=["invoice-intake"])


def _vendor_scope(user: User) -> str | None:
    roles = {role.code for role in user.roles}
    if "VENDOR" in roles:
        if not user.vendor_code:
            raise HTTPException(status_code=403, detail="Vendor identity is required")
        return user.vendor_code
    if "RECONCILIATION" in roles or "ADMIN" in roles or "SYSTEM_ADMIN" in roles:
        return None
    raise HTTPException(status_code=403, detail="Invoice intake access denied")


def _view(document: InvoiceIntakeDocument, po_number: str | None) -> InvoiceIntakeResponse:
    return InvoiceIntakeResponse.model_validate(document).model_copy(
        update={"suggested_po_number": po_number}
    )


@router.post("/upload", response_model=InvoiceIntakeBatchResponse, status_code=201)
async def upload_invoice_pdfs(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvoiceIntakeBatchResponse:
    vendor_scope = _vendor_scope(user)
    try:
        if not files or len(files) > MAX_BATCH_FILES:
            raise InvoiceIntakeError(f"Upload between 1 and {MAX_BATCH_FILES} PDF files")
        uploads: list[tuple[str, bytes]] = []
        total_bytes = 0
        for file in files:
            content = await file.read(MAX_PDF_BYTES + 1)
            if len(content) > MAX_PDF_BYTES:
                raise InvoiceIntakeError(f"Each invoice PDF must not exceed {MAX_PDF_BYTES} bytes")
            total_bytes += len(content)
            if total_bytes > MAX_BATCH_BYTES:
                raise InvoiceIntakeError(
                    f"Invoice upload batch must not exceed {MAX_BATCH_BYTES} bytes"
                )
            uploads.append((file.filename or "invoice.pdf", content))
        documents, duplicates = ingest_invoice_pdfs(
            db,
            uploads,
            user.email,
            vendor_scope,
        )
    except InvoiceIntakeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    views_by_id = {
        document.id: _view(document, po_number)
        for document, po_number in list_unreconciled_documents(db, vendor_scope)
    }
    return InvoiceIntakeBatchResponse(
        uploaded_files=len(files),
        separated_invoices=len(documents),
        duplicate_invoices=duplicates,
        documents=[views_by_id[item.id] for item in documents],
    )


@router.get("", response_model=list[InvoiceIntakeResponse])
def read_unreconciled_invoice_documents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InvoiceIntakeResponse]:
    return [
        _view(document, po_number)
        for document, po_number in list_unreconciled_documents(db, _vendor_scope(user))
    ]


@router.get("/{document_id}/pdf")
def download_invoice_pdf(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    vendor_scope = _vendor_scope(user)
    document = db.get(InvoiceIntakeDocument, document_id)
    if document is None or (
        vendor_scope is not None and document.detected_vendor_code != vendor_scope
    ):
        raise HTTPException(status_code=404, detail="Invoice document not found")
    try:
        path = document_path(document)
    except InvoiceIntakeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type="application/pdf", filename=document.original_filename)
