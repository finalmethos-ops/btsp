from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LoadoutEventStatus = Literal["draft", "open", "closed"]
LoadoutAssignmentStatus = Literal[
    "not_started",
    "in_progress",
    "exceptions_present",
    "ready_for_final_review",
    "signed_complete",
    "released_from_venue",
]
LoadoutItemStatus = Literal[
    "assigned",
    "found",
    "damaged",
    "missing",
    "quantity_mismatch",
    "substituted",
    "removed",
    "signed_off",
]


class StoreLoadoutEventWrite(BaseModel):
    status: LoadoutEventStatus = "draft"
    opens_at: datetime | None = None
    loadout_deadline: datetime | None = None
    default_loadout_zone: str | None = Field(default=None, max_length=255)
    venue_departure_notes: str | None = Field(default=None, max_length=5000)
    dock_master_email: str | None = Field(default=None, max_length=320)


class StoreLoadoutEventResponse(StoreLoadoutEventWrite):
    id: str
    event_id: str
    event_name: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class StoreLoadoutItemAssignmentWrite(BaseModel):
    vendor_hall_inventory_item_id: str
    quantity_assigned: int = Field(ge=1)
    vehicle_label: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=5000)


class StoreLoadoutItemCheckinWrite(BaseModel):
    status: LoadoutItemStatus
    quantity_found: int = Field(default=0, ge=0)
    damage_notes: str | None = Field(default=None, max_length=5000)
    missing_notes: str | None = Field(default=None, max_length=5000)


class StoreLoadoutTeamWrite(BaseModel):
    team_name: str | None = Field(default=None, max_length=255)
    team_member_emails: list[str] = Field(default_factory=list, max_length=100)
    team_lead_emails: list[str] = Field(default_factory=list, max_length=20)
    vehicle_labels: list[str] = Field(default_factory=list, max_length=20)


class StoreLoadoutFinalReviewWrite(BaseModel):
    notes: str | None = Field(default=None, max_length=5000)


class StoreLoadoutVehicleStatusWrite(BaseModel):
    status: Literal["expected", "loading", "loaded", "departed"]


class StoreLoadoutItemCheckinResponse(BaseModel):
    id: str
    loadout_item_id: str
    assignment_id: str
    status: LoadoutItemStatus
    quantity_found: int
    damage_notes: str | None
    missing_notes: str | None
    checked_by: str
    checked_at: datetime


class StoreLoadoutSignoffWrite(BaseModel):
    signer_name: str = Field(min_length=1, max_length=255)
    signer_email: str = Field(min_length=3, max_length=320)
    signature_text: str = Field(min_length=1, max_length=255)
    exception_summary: str | None = Field(default=None, max_length=5000)


class StoreLoadoutSignoffResponse(BaseModel):
    id: str
    assignment_id: str
    signer_name: str
    signer_email: str
    signature_text: str
    exception_summary: str | None
    signed_at: datetime


class StoreLoadoutAssignmentWrite(BaseModel):
    store_number: str = Field(min_length=1, max_length=32)
    entity_code: str | None = Field(default=None, max_length=64)
    pickup_priority: int = Field(default=100, ge=1)
    loadout_zone: str | None = Field(default=None, max_length=255)
    distance_miles: Decimal | None = Field(default=None, ge=0)
    estimated_drive_minutes: int | None = Field(default=None, ge=0)
    recommended_departure_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=5000)
    vehicle_labels: list[str] = Field(default_factory=list, max_length=20)
    items: list[StoreLoadoutItemAssignmentWrite] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_items(self) -> "StoreLoadoutAssignmentWrite":
        item_ids = [item.vendor_hall_inventory_item_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Duplicate inventory items in one assignment are not allowed")
        return self


class StoreLoadoutRouteEstimateResponse(BaseModel):
    store_number: str
    distance_miles: Decimal
    estimated_drive_minutes: int
    recommended_departure_at: datetime
    arrival_target_at: datetime
    source: str


class StoreLoadoutRouteRecalculateResponse(BaseModel):
    updated: int
    failed_store_numbers: list[str] = Field(default_factory=list)


class StoreLoadoutReassignmentWrite(BaseModel):
    vehicle_labels: list[str] = Field(default_factory=list, max_length=20)
    notes: str | None = Field(default=None, max_length=5000)
    items: list[StoreLoadoutItemAssignmentWrite] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_items(self) -> "StoreLoadoutReassignmentWrite":
        item_ids = [item.vendor_hall_inventory_item_id for item in self.items]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Duplicate inventory items in one reassignment are not allowed")
        return self


class StoreLoadoutItemResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    assignment_id: str
    event_id: str
    vendor_hall_booth_id: str
    vendor_hall_inventory_item_id: str
    vendor_code: str
    vendor_name: str | None
    booth_number: str
    item_name: str
    model_number: str | None
    serial_number: str | None
    quantity_assigned: int
    quantity_found: int
    condition: str
    status: LoadoutItemStatus
    notes: str | None
    damage_notes: str | None
    missing_notes: str | None
    vehicle_label: str | None
    updated_at: datetime


class StoreLoadoutItemAttachmentResponse(BaseModel):
    id: str
    assignment_id: str
    loadout_item_id: str
    attachment_type: Literal["photo", "other"]
    filename: str
    content_type: str
    uploaded_by: str
    created_at: datetime


class StoreLoadoutAssignmentResponse(BaseModel):
    id: str
    store_loadout_event_id: str
    event_id: str
    event_name: str
    store_number: str
    store_name: str | None
    store_manager_name: str | None
    store_manager_email: str | None
    store_phone: str | None
    store_address: str | None
    entity_code: str | None
    status: LoadoutAssignmentStatus
    pickup_priority: int
    loadout_zone: str | None
    distance_miles: Decimal | None
    estimated_drive_minutes: int | None
    recommended_departure_at: datetime | None
    notes: str | None
    team_name: str | None
    team_member_emails: list[str] = Field(default_factory=list)
    team_lead_emails: list[str] = Field(default_factory=list)
    vehicle_labels: list[str] = Field(default_factory=list)
    vehicle_statuses: dict[str, str] = Field(default_factory=dict)
    final_review_requested_at: datetime | None
    final_review_requested_by: str | None
    final_review_completed_at: datetime | None
    final_review_completed_by: str | None
    final_review_notes: str | None
    item_count: int
    exception_count: int
    signed_at: datetime | None
    signed_by: str | None
    released_at: datetime | None
    released_by: str | None
    updated_at: datetime
    items: list[StoreLoadoutItemResponse] = Field(default_factory=list)


class StoreLoadoutTeamSummary(BaseModel):
    team_name: str
    status: str
    assignment_total: int
    reviewed: int
    signed: int
    released: int
    completion_percentage: float


class StoreLoadoutSummaryResponse(BaseModel):
    event_id: str
    event_name: str
    store_loadout_event_id: str | None
    assignment_total: int
    not_started: int
    in_progress: int
    exceptions_present: int
    ready_for_final_review: int
    signed_complete: int
    released_from_venue: int
    item_total: int
    items_found: int
    items_damaged: int
    items_missing: int
    completion_percentage: float = 0
    teams: list[StoreLoadoutTeamSummary] = Field(default_factory=list)
