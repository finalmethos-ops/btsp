from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.event_management import (
    EventAttendance,
    EventMembership,
    EventSubEventRegistration,
    ManagedEvent,
    ManagedSubEvent,
)
from app.models.identity import User
from app.schemas.event_attendance import (
    EventAttendanceMemberResponse,
    EventAttendancePassLookupResponse,
    EventAttendancePassResponse,
    EventAttendancePassSubEventResponse,
    EventAttendanceRosterResponse,
)
from app.services.event_access_service import (
    event_operations_are_locked,
    membership_has_sub_event_access,
)


class EventAttendanceError(ValueError):
    pass


def _check_in_enabled(sub_event: ManagedSubEvent) -> None:
    if "check-in" not in sub_event.module_codes:
        raise EventAttendanceError("Check-in is not enabled for this sub-event")


def _pass_code(membership_id: str) -> str:
    return f"BTSP-{membership_id[:8].upper()}"


def _membership_from_pass_code(db: Session, pass_code: str) -> EventMembership | None:
    normalized = pass_code.strip().upper().replace(" ", "")
    if normalized.startswith("BTSP-"):
        normalized = normalized[5:]
    if len(normalized) < 8:
        return None
    matches = db.scalars(
        select(EventMembership).where(EventMembership.id.ilike(f"{normalized[:8]}%"))
    ).all()
    return matches[0] if len(matches) == 1 else None


def attendance_roster(db: Session, sub_event_id: str) -> EventAttendanceRosterResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _check_in_enabled(sub_event)
    rows = db.execute(
        select(EventMembership, User, EventAttendance)
        .join(User, User.id == EventMembership.user_id)
        .outerjoin(
            EventAttendance,
            (EventAttendance.membership_id == EventMembership.id)
            & (EventAttendance.sub_event_id == sub_event_id),
        )
        .where(
            EventMembership.event_id == sub_event.event_id,
            EventMembership.is_active.is_(True),
        )
        .order_by(User.display_name, User.email)
    ).all()
    specifically_registered = set(
        db.scalars(
            select(EventSubEventRegistration.membership_id).where(
                EventSubEventRegistration.sub_event_id == sub_event_id
            )
        ).all()
    )
    rows = [
        row
        for row in rows
        if not row[0].sub_event_scope_configured or row[0].id in specifically_registered
    ]
    members = [
        EventAttendanceMemberResponse(
            membership_id=membership.id,
            user_id=user.id,
            display_name=user.display_name,
            email=user.email,
            membership_type=membership.membership_type,
            vendor_code=membership.vendor_code,
            entity_code=membership.entity_code,
            pass_code=_pass_code(membership.id),
            status=attendance.status if attendance else "registered",
            checked_in_at=attendance.checked_in_at if attendance else None,
            checked_out_at=attendance.checked_out_at if attendance else None,
        )
        for membership, user, attendance in rows
    ]
    return EventAttendanceRosterResponse(
        event_id=sub_event.event_id,
        sub_event_id=sub_event.id,
        sub_event_name=sub_event.name,
        capacity=sub_event.capacity,
        registered_total=len(members),
        checked_in_total=sum(item.status == "checked_in" for item in members),
        checked_out_total=sum(item.status == "checked_out" for item in members),
        onsite_total=sum(item.status == "checked_in" for item in members),
        members=members,
    )


def my_attendance_passes(db: Session, user: User) -> list[EventAttendancePassResponse]:
    rows = db.execute(
        select(EventMembership, ManagedEvent)
        .join(ManagedEvent, ManagedEvent.id == EventMembership.event_id)
        .where(
            EventMembership.user_id == user.id,
            EventMembership.is_active.is_(True),
        )
        .order_by(ManagedEvent.starts_at.desc())
    ).all()
    passes: list[EventAttendancePassResponse] = []
    for membership, event in rows:
        sub_events = db.scalars(
            select(ManagedSubEvent)
            .where(ManagedSubEvent.event_id == event.id)
            .order_by(ManagedSubEvent.starts_at, ManagedSubEvent.name)
        ).all()
        visible_sub_events = [
            sub_event
            for sub_event in sub_events
            if membership_has_sub_event_access(db, membership, sub_event.id)
        ]
        attendance_by_sub_event = {
            attendance.sub_event_id: attendance
            for attendance in db.scalars(
                select(EventAttendance).where(EventAttendance.membership_id == membership.id)
            ).all()
        }
        passes.append(
            EventAttendancePassResponse(
                event_id=event.id,
                event_name=event.name,
                membership_id=membership.id,
                display_name=user.display_name,
                email=user.email,
                membership_type=membership.membership_type,
                vendor_code=membership.vendor_code,
                entity_code=membership.entity_code,
                pass_code=_pass_code(membership.id),
                sub_events=[
                    EventAttendancePassSubEventResponse(
                        id=sub_event.id,
                        event_id=event.id,
                        name=sub_event.name,
                        location=sub_event.location,
                        starts_at=sub_event.starts_at,
                        ends_at=sub_event.ends_at,
                        module_codes=sub_event.module_codes,
                        check_in_enabled="check-in" in sub_event.module_codes,
                        status=(
                            attendance_by_sub_event[sub_event.id].status
                            if sub_event.id in attendance_by_sub_event
                            else "registered"
                        ),
                        checked_in_at=(
                            attendance_by_sub_event[sub_event.id].checked_in_at
                            if sub_event.id in attendance_by_sub_event
                            else None
                        ),
                        checked_out_at=(
                            attendance_by_sub_event[sub_event.id].checked_out_at
                            if sub_event.id in attendance_by_sub_event
                            else None
                        ),
                    )
                    for sub_event in visible_sub_events
                ],
            )
        )
    return passes


def update_attendance_by_pass_code(
    db: Session, sub_event_id: str, pass_code: str, status: str, actor: str
) -> EventAttendancePassLookupResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _check_in_enabled(sub_event)
    membership = _membership_from_pass_code(db, pass_code)
    if membership is None:
        raise EventAttendanceError("Pass code was not found")
    if membership.event_id != sub_event.event_id or not membership.is_active:
        raise EventAttendanceError("Pass is not active for this event")
    if not membership_has_sub_event_access(db, membership, sub_event_id):
        raise EventAttendanceError("Pass is not assigned to this sub-event")
    roster = update_attendance(db, sub_event_id, membership.id, status, actor)
    if roster is None:
        return None
    member = next(
        (item for item in roster.members if item.membership_id == membership.id),
        None,
    )
    if member is None:
        raise EventAttendanceError("Pass is not assigned to this sub-event")
    return EventAttendancePassLookupResponse(roster=roster, member=member)


def update_attendance(
    db: Session, sub_event_id: str, membership_id: str, status: str, actor: str
) -> EventAttendanceRosterResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _check_in_enabled(sub_event)
    if event_operations_are_locked(db, sub_event.event_id):
        raise EventAttendanceError(
            "Event attendance is locked because the event is cancelled or settlement is closed"
        )
    membership = db.get(EventMembership, membership_id)
    if membership is None or membership.event_id != sub_event.event_id or not membership.is_active:
        raise EventAttendanceError("Member is not active for this event")
    attendance = db.scalar(
        select(EventAttendance).where(
            EventAttendance.sub_event_id == sub_event_id,
            EventAttendance.membership_id == membership_id,
        )
    )
    if attendance is None:
        attendance = EventAttendance(
            event_id=sub_event.event_id,
            sub_event_id=sub_event_id,
            membership_id=membership_id,
            updated_by=actor,
        )
        db.add(attendance)
    now = datetime.now(UTC)
    if status == "checked_in" and attendance.status != "checked_in" and sub_event.capacity:
        onsite = db.scalar(
            select(func.count(EventAttendance.id)).where(
                EventAttendance.sub_event_id == sub_event_id,
                EventAttendance.status == "checked_in",
            )
        )
        if (onsite or 0) >= sub_event.capacity:
            raise EventAttendanceError("Sub-event capacity has been reached")
    attendance.status = status
    attendance.updated_by = actor
    if status == "checked_in":
        attendance.checked_in_at = now
        attendance.checked_out_at = None
    elif status == "checked_out":
        if attendance.checked_in_at is None:
            raise EventAttendanceError("Member must check in before checking out")
        attendance.checked_out_at = now
    else:
        raise EventAttendanceError("Unsupported attendance status")
    db.commit()
    return attendance_roster(db, sub_event_id)
