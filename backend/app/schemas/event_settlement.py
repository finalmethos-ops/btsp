from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

SettlementStatus = Literal[
    "draft",
    "collecting_evidence",
    "exceptions_present",
    "ready_for_review",
    "approved",
    "closed",
]


class EventSettlementWrite(BaseModel):
    status: SettlementStatus = "draft"
    notes: str | None = Field(default=None, max_length=5000)


class EventSettlementExceptionWrite(BaseModel):
    exception_type: str = Field(min_length=2, max_length=48)
    severity: str = Field(default="medium", min_length=2, max_length=24)
    reference_type: str | None = Field(default=None, max_length=48)
    reference_id: str | None = Field(default=None, max_length=64)
    description: str = Field(min_length=3, max_length=5000)


class EventSettlementExceptionResolutionWrite(BaseModel):
    resolution_notes: str | None = Field(default=None, max_length=5000)


class EventSettlementExceptionResponse(BaseModel):
    id: str
    exception_type: str
    severity: str
    status: str
    reference_type: str | None
    reference_id: str | None
    description: str
    created_at: datetime
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None


class EventSettlementSummaryResponse(BaseModel):
    event_id: str
    event_name: str
    settlement_event_id: str | None
    status: SettlementStatus
    vendor_hall_status: str | None = None
    vendor_hall_closeout_ready: bool | None = None
    order_total: int
    order_released: int
    approved_units: int
    approved_spend: Decimal
    loadout_assignment_total: int
    loadout_signed: int
    loadout_released: int
    loadout_exception_assignments: int
    loadout_final_review_pending: int
    ordered_not_loaded_count: int
    loaded_not_ordered_count: int
    quantity_mismatch_count: int
    open_exception_count: int
    readiness_percentage: Decimal
    exceptions: list[EventSettlementExceptionResponse]
    notes: str | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    closed_at: datetime | None = None
    closed_by: str | None = None
    updated_at: datetime | None = None
