from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InvoiceIntakeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    page_start: int
    page_end: int
    invoice_number: str | None
    detected_vendor_code: str | None
    detected_store_number: str | None
    detected_po_number: str | None
    suggested_purchase_order_id: str | None
    suggested_po_number: str | None = None
    status: str
    uploaded_by: str
    uploader_vendor_code: str | None
    created_at: datetime


class InvoiceIntakeBatchResponse(BaseModel):
    uploaded_files: int
    separated_invoices: int
    duplicate_invoices: int
    documents: list[InvoiceIntakeResponse]
