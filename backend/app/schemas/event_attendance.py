from datetime import datetime
from typing import Literal

from pydantic import BaseModel

AttendanceStatus = Literal["registered", "checked_in", "checked_out"]


class EventAttendanceUpdate(BaseModel):
    status: Literal["checked_in", "checked_out"]


class EventAttendancePassLookup(BaseModel):
    pass_code: str
    status: Literal["checked_in", "checked_out"] = "checked_in"


class EventAttendanceMemberResponse(BaseModel):
    membership_id: str
    user_id: int
    display_name: str
    email: str
    membership_type: Literal["staff", "vendor", "franchise_representative", "executive", "admin"]
    vendor_code: str | None
    entity_code: str | None
    status: AttendanceStatus
    checked_in_at: datetime | None
    checked_out_at: datetime | None


class EventAttendanceRosterResponse(BaseModel):
    event_id: str
    sub_event_id: str
    sub_event_name: str
    capacity: int | None
    registered_total: int
    checked_in_total: int
    checked_out_total: int
    onsite_total: int
    members: list[EventAttendanceMemberResponse]


class EventAttendancePassLookupResponse(BaseModel):
    roster: EventAttendanceRosterResponse
    member: EventAttendanceMemberResponse


class EventAttendancePassSubEventResponse(BaseModel):
    id: str
    event_id: str
    name: str
    location: str
    starts_at: datetime
    ends_at: datetime
    module_codes: list[str]
    check_in_enabled: bool
    status: AttendanceStatus
    checked_in_at: datetime | None
    checked_out_at: datetime | None


class EventAttendancePassResponse(BaseModel):
    event_id: str
    event_name: str
    membership_id: str
    display_name: str
    email: str
    membership_type: Literal["staff", "vendor", "franchise_representative", "executive", "admin"]
    vendor_code: str | None
    entity_code: str | None
    pass_code: str
    sub_events: list[EventAttendancePassSubEventResponse]
