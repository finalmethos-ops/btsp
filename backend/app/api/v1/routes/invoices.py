from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.invoice import VendorInvoiceCreate, VendorInvoiceResponse
from app.services.invoice_service import (
    InvoiceError,
    create_vendor_invoice,
    get_vendor_invoice,
    list_vendor_invoices,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("", response_model=VendorInvoiceResponse)
def post_invoice(
    payload: VendorInvoiceCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("invoices.manage")),
) -> VendorInvoiceResponse:
    try:
        invoice, created = create_vendor_invoice(db, payload, user.email)
    except InvoiceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return VendorInvoiceResponse.model_validate(invoice)


@router.get("", response_model=list[VendorInvoiceResponse])
def read_invoices(
    vendor_code: str | None = None,
    invoice_status: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("invoices.read")),
) -> list[VendorInvoiceResponse]:
    return [
        VendorInvoiceResponse.model_validate(item)
        for item in list_vendor_invoices(db, vendor_code, invoice_status)
    ]


@router.get("/{invoice_id}", response_model=VendorInvoiceResponse)
def read_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("invoices.read")),
) -> VendorInvoiceResponse:
    invoice = get_vendor_invoice(db, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return VendorInvoiceResponse.model_validate(invoice)
