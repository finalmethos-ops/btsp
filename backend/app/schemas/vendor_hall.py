from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

BoothStatus = Literal[
    "draft",
    "inventory_submitted",
    "ready_for_inspection",
    "checkin_in_progress",
    "fully_checked_in",
    "exceptions_present",
    "admin_reviewed",
    "closed",
]
ItemStatus = Literal[
    "expected",
    "checked_in",
    "damaged",
    "not_in_booth",
    "quantity_mismatch",
    "purchased",
    "removed",
]
ItemCondition = Literal["new", "floor_model", "open_box", "used", "damaged", "unknown"]


class VendorHallEventWrite(BaseModel):
    sub_event_id: str | None = None
    status: Literal["draft", "open", "closed"] = "draft"
    opens_at: datetime | None = None
    vendor_submission_deadline: datetime | None = None
    staff_checkin_opens_at: datetime | None = None
    staff_checkin_deadline: datetime | None = None
    allow_vendor_edits_after_submission: bool = False
    require_staff_checkin: bool = True


class VendorHallEventResponse(VendorHallEventWrite):
    id: str
    event_id: str
    event_name: str
    sub_event_name: str | None
    created_at: datetime
    updated_at: datetime


class VendorHallBoothResponse(BaseModel):
    id: str
    vendor_hall_event_id: str
    event_vendor_booth_id: str | None
    assigned_staff_membership_id: str | None = None
    assigned_staff_display_name: str | None = None
    event_id: str
    event_name: str
    vendor_code: str
    vendor_name: str | None
    booth_number: str
    booth_name: str
    floor_map_zone: str | None
    map_x: Decimal | None
    map_y: Decimal | None
    map_width: Decimal | None
    map_height: Decimal | None
    map_manually_adjusted: bool = False
    status: BoothStatus
    submitted_at: datetime | None
    checkin_started_at: datetime | None
    checkin_completed_at: datetime | None
    exceptions_count: int = 0
    available_for_sale_count: int = 0
    inventory_count: int = 0
    updated_at: datetime


class VendorHallBoothMapPositionWrite(BaseModel):
    floor_map_zone: str | None = Field(default=None, max_length=255)
    map_x: Decimal | None = Field(default=None, ge=0)
    map_y: Decimal | None = Field(default=None, ge=0)
    map_width: Decimal | None = Field(default=None, ge=0)
    map_height: Decimal | None = Field(default=None, ge=0)


class VendorHallBoothStaffAssignmentWrite(BaseModel):
    membership_id: str | None = None


class VendorHallSummaryResponse(BaseModel):
    event_id: str
    event_name: str
    vendor_hall_event_id: str | None
    booth_total: int
    inventory_submitted: int
    checkin_in_progress: int
    fully_checked_in: int
    exceptions_present: int
    closed: int
    completion_percentage: Decimal
    inventory_item_total: int = 0
    inventory_items_checked: int = 0
    inventory_completion_percentage: Decimal = Decimal("0.00")
    closeout_ready: bool = False
    vendors_not_submitted: list[VendorHallBoothResponse] = Field(default_factory=list)


class VendorHallInventoryItemWrite(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_number: str | None = Field(default=None, max_length=128)
    serial_number: str | None = Field(default=None, max_length=128)
    item_name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    quantity_expected: int = Field(default=1, ge=1)
    unit_price: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    condition: ItemCondition = "unknown"
    status: ItemStatus = "expected"
    available_for_sale: bool = False
    sell_to_buddys_price: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=5000)
    vendor_notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def sale_price_requires_sale_flag(self) -> "VendorHallInventoryItemWrite":
        if self.sell_to_buddys_price is not None and not self.available_for_sale:
            raise ValueError("sell_to_buddys_price requires available_for_sale")
        return self


class VendorHallInventoryStaffUpdate(BaseModel):
    quantity_checked_in: int = Field(default=0, ge=0)
    condition: ItemCondition = "unknown"
    staff_notes: str | None = Field(default=None, max_length=5000)


class VendorHallInventoryImportResponse(BaseModel):
    id: str
    vendor_hall_booth_id: str
    filename: str
    content_type: str
    row_count: int
    accepted_count: int
    rejected_count: int
    status: str
    error_summary: str | None
    uploaded_by: str
    uploaded_at: datetime
    completed_at: datetime | None


class VendorHallItemAttachmentResponse(BaseModel):
    id: str
    inventory_item_id: str
    attachment_type: Literal["photo", "spec_sheet", "other"]
    filename: str
    content_type: str
    uploaded_by: str
    uploaded_at: datetime


class VendorHallInventoryItemResponse(VendorHallInventoryItemWrite):
    id: str
    vendor_hall_booth_id: str
    event_id: str
    vendor_code: str
    quantity_checked_in: int
    staff_notes: str | None
    validated: bool = False
    attachments: list[VendorHallItemAttachmentResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class VendorHallItemCheckinWrite(BaseModel):
    status: ItemStatus
    quantity_checked: int = Field(default=0, ge=0)
    condition: ItemCondition | None = None
    damage_notes: str | None = Field(default=None, max_length=5000)
    exception_notes: str | None = Field(default=None, max_length=5000)
    staff_notes: str | None = Field(default=None, max_length=5000)


class VendorHallInventorySplitWrite(BaseModel):
    split_quantity: int = Field(ge=1)
    status: ItemStatus = "damaged"
    notes: str | None = Field(default=None, max_length=5000)


class VendorHallItemCheckinResponse(BaseModel):
    id: str
    inventory_item_id: str
    vendor_hall_booth_id: str
    status: ItemStatus
    quantity_checked: int
    condition: ItemCondition | None
    damage_notes: str | None
    exception_notes: str | None
    checked_by: str
    checked_at: datetime


class VendorHallBoothCheckinWrite(BaseModel):
    notes: str | None = Field(default=None, max_length=5000)


class VendorHallBoothCheckinResponse(BaseModel):
    id: str
    vendor_hall_booth_id: str
    status: BoothStatus
    started_by: str
    started_at: datetime
    completed_by: str | None
    completed_at: datetime | None
    completion_percentage: Decimal
    items_expected: int
    items_checked: int
    exceptions_count: int
    notes: str | None


class VendorHallFloorMapWrite(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    layout_json: dict = Field(default_factory=dict)
    is_active: bool = True


class VendorHallFloorMapResponse(BaseModel):
    id: str
    vendor_hall_event_id: str
    name: str
    has_image: bool
    layout_json: dict
    uploaded_by: str
    uploaded_at: datetime
    is_active: bool


class VendorHallFloorMapStatusResponse(BaseModel):
    event_id: str
    event_name: str
    floor_map: VendorHallFloorMapResponse | None
    booths: list[VendorHallBoothResponse]


class VendorHallDirectoryBoothResponse(BaseModel):
    id: str
    booth_number: str
    booth_name: str
    vendor_name: str | None
    floor_map_zone: str | None
    map_x: Decimal | None
    map_y: Decimal | None
    map_width: Decimal | None
    map_height: Decimal | None
    attendees: list[str] = Field(default_factory=list)
    is_saved: bool = False
    is_visited: bool = False


class VendorHallDirectoryResponse(BaseModel):
    event_id: str
    event_name: str
    floor_map: VendorHallFloorMapResponse | None
    booths: list[VendorHallDirectoryBoothResponse]


class VendorHallDirectoryMessageWrite(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=5000)


class VendorHallDirectoryMessageResponse(BaseModel):
    sent_count: int
