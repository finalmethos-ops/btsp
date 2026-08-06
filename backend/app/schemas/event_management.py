from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EventStatus = Literal["draft", "published", "completed", "cancelled"]
MembershipType = Literal[
    "staff",
    "vendor",
    "franchise_representative",
    "executive",
    "admin",
    "team_lead",
    "dockmaster",
    "overseer",
]
LoadoutRole = Literal["team_lead", "dockmaster", "overseer"]
EVENT_MODULES = {
    "product-slides": "Product slide builder",
    "live-display": "Live display and presentation control",
    "presentation": "Live presentation",
    "ordering": "Entity product ordering",
    "polling": "Live polls and voting",
    "check-in": "Registration and check-in",
    "staff-tasks": "Onsite staff tasks",
    "vendor-booths": "Vendor booth profiles",
    "vendor-hall-setup": "Vendor hall setup",
    "vendor-hall-inventory": "Vendor inventory management",
    "event-inventory": "Event inventory suite",
    "store-loadout": "Store loadout",
    "event-settlement": "Event settlement and reconciliation",
    "vendor-buy-fair": "Vendor buy fair ordering",
    "order-review": "Event order review",
}
SETUP_EVENT_MODULES = {
    code: name
    for code, name in EVENT_MODULES.items()
    if code not in {"presentation", "order-review"}
}


class EventWrite(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=96, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=10_000)
    status: EventStatus = "draft"
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(default="America/New_York", min_length=1, max_length=64)
    venue_name: str = Field(min_length=1, max_length=255)
    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=128)
    state_code: str = Field(min_length=1, max_length=32)
    postal_code: str = Field(min_length=1, max_length=24)
    country_code: str = Field(default="US", min_length=2, max_length=2)
    theme_primary_color: str = Field(default="#07142c", pattern=r"^#[0-9a-fA-F]{6}$")
    theme_accent_color: str = Field(default="#ffd400", pattern=r"^#[0-9a-fA-F]{6}$")

    @model_validator(mode="after")
    def valid_dates(self) -> "EventWrite":
        if self.ends_at <= self.starts_at:
            raise ValueError("Event end must be after its start")
        return self


class EventCancellationWrite(BaseModel):
    reason: str = Field(min_length=3, max_length=5000)


class SubEventWrite(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    starts_at: datetime
    ends_at: datetime
    location: str = Field(min_length=1, max_length=255)
    status: EventStatus = "draft"
    module_codes: list[str] = Field(default_factory=list, max_length=50)
    capacity: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def valid_dates(self) -> "SubEventWrite":
        if self.ends_at <= self.starts_at:
            raise ValueError("Sub-event end must be after its start")
        return self


class SubEventModulesWrite(BaseModel):
    module_codes: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def valid_modules(self) -> "SubEventModulesWrite":
        unknown = sorted(set(self.module_codes) - EVENT_MODULES.keys())
        if unknown:
            raise ValueError(f"Unknown event modules: {', '.join(unknown)}")
        self.module_codes = sorted(set(self.module_codes))
        return self


class EventModuleResponse(BaseModel):
    code: str
    name: str


class EventAccountDirectoryResponse(BaseModel):
    id: int
    email: str
    display_name: str
    is_active: bool
    vendor_codes: list[str] = Field(default_factory=list)


class EventMembershipCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    membership_type: MembershipType
    vendor_code: str | None = Field(default=None, max_length=64)
    vendor_codes: list[str] = Field(default_factory=list, max_length=100)
    entity_code: str | None = Field(default=None, max_length=64)
    module_codes: list[str] = Field(default_factory=list, max_length=50)
    task_scope: str | None = Field(default=None, max_length=5000)
    is_active: bool = True

    @model_validator(mode="after")
    def valid_membership(self) -> "EventMembershipCreate":
        if self.membership_type == "vendor" and not (self.vendor_code or self.vendor_codes):
            raise ValueError("Vendor event accounts require a vendor code")
        self.vendor_codes = sorted(
            {code.strip().upper() for code in self.vendor_codes if code.strip()}
        )
        if self.membership_type == "vendor" and self.vendor_code:
            self.vendor_code = self.vendor_code.strip().upper()
            if self.vendor_code not in self.vendor_codes:
                self.vendor_codes.insert(0, self.vendor_code)
        if self.membership_type == "franchise_representative" and not self.entity_code:
            raise ValueError("Franchise representative accounts require an entity code")
        if self.entity_code:
            self.entity_code = self.entity_code.strip().upper()
        return self


class EventMembershipUpdate(EventMembershipCreate):
    """Fully editable event registration details for an existing attendee."""


class EventMembershipRoleUpdate(BaseModel):
    membership_type: MembershipType


class EventMembershipLoadoutRoleUpdate(BaseModel):
    loadout_role: LoadoutRole | None = None


class EventVendorMembershipUpdate(BaseModel):
    vendor_codes: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def normalize_codes(self) -> "EventVendorMembershipUpdate":
        self.vendor_codes = sorted(
            {code.strip().upper() for code in self.vendor_codes if code.strip()}
        )
        if not self.vendor_codes:
            raise ValueError("At least one vendor account is required")
        return self


class SubEventResponse(SubEventWrite):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_id: str


class EventMembershipResponse(BaseModel):
    id: str
    event_id: str
    user_id: int
    email: str
    display_name: str
    membership_type: MembershipType
    loadout_role: LoadoutRole | None = None
    vendor_code: str | None
    vendor_codes: list[str] = Field(default_factory=list)
    entity_code: str | None
    module_codes: list[str]
    task_scope: str | None
    is_active: bool
    sub_event_scope_configured: bool
    sub_event_ids: list[str] = Field(default_factory=list)
    sub_event_roles: dict[str, LoadoutRole | None] = Field(default_factory=dict)


class EventSubEventRegistrationWrite(BaseModel):
    sub_event_ids: list[str] = Field(default_factory=list, max_length=500)
    roles: dict[str, LoadoutRole | None] = Field(default_factory=dict)


class EventResponse(EventWrite):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_by: str
    created_at: datetime
    cancelled_at: datetime | None = None
    cancelled_by: str | None = None
    cancellation_reason: str | None = None
    has_branding: bool = False
    has_venue_map: bool = False
    sub_events: list[SubEventResponse] = Field(default_factory=list)
    memberships: list[EventMembershipResponse] = Field(default_factory=list)
