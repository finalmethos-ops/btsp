from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ReconciliationCreate(BaseModel):
    invoice_id: str


class ReconciliationExceptionResolution(BaseModel):
    disposition: str = Field(pattern="^(accept_variance|vendor_credit|corrected_invoice)$")
    note: str = Field(min_length=1, max_length=1000)


class ReconciliationDecision(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    note: str = Field(min_length=1, max_length=1000)


class ReconciliationExceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_line_id: int | None
    exception_type: str
    expected_amount: Decimal
    actual_amount: Decimal
    difference_amount: Decimal
    status: str
    disposition: str | None
    resolution_note: str | None
    resolved_by: str | None
    resolved_at: datetime | None
    created_at: datetime


class ReconciliationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    from_status: str
    to_status: str
    note: str
    actor: str
    created_at: datetime


class ReconciliationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_id: str
    purchase_order_id: str
    status: str
    created_by: str
    approved_by: str | None
    approved_at: datetime | None
    rejected_by: str | None
    rejected_at: datetime | None
    decision_note: str | None
    created_at: datetime
    updated_at: datetime
    exceptions: list[ReconciliationExceptionResponse]
    events: list[ReconciliationEventResponse]
