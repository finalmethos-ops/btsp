from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth.security import hash_password
from app.models.catalog import CatalogVendor
from app.models.event_management import (
    EventBrandingAsset,
    EventCalendarEntry,
    EventMembership,
    EventPoll,
    EventPresentationState,
    EventSubEventRegistration,
    EventVendorBooth,
    EventVenueMapAsset,
    ManagedEvent,
    ManagedSubEvent,
)
from app.models.event_snapshot import EventSnapshot
from app.models.identity import User
from app.schemas.event_management import (
    EVENT_MODULES,
    EventAccountDirectoryResponse,
    EventCancellationWrite,
    EventMembershipCreate,
    EventMembershipLoadoutRoleUpdate,
    EventMembershipResponse,
    EventMembershipRoleUpdate,
    EventMembershipUpdate,
    EventResponse,
    EventSubEventRegistrationWrite,
    EventVendorMembershipUpdate,
    EventWrite,
    SubEventModulesWrite,
    SubEventWrite,
)
from app.services.event_access_service import (
    event_operations_are_locked,
    event_settlement_is_closed,
)
from app.services.upload_validation import content_matches_declared_type
from app.services.vendor_access_service import vendor_codes_for_user


class EventManagementError(ValueError):
    pass


def update_membership_role(
    db: Session,
    event_id: str,
    membership_id: str,
    payload: EventMembershipRoleUpdate,
    actor: str,
) -> EventResponse | None:
    event = get_event(db, event_id)
    membership = db.scalar(
        select(EventMembership).where(
            EventMembership.id == membership_id,
            EventMembership.event_id == event_id,
        )
    )
    if event is None or membership is None:
        return None
    membership.membership_type = payload.membership_type
    if payload.membership_type != "vendor":
        membership.vendor_code = None
        membership.vendor_codes = []
    _lifecycle_snapshot(
        db,
        event_type="event.membership.role.updated",
        entity_type="event_membership",
        entity_id=membership.id,
        actor=actor,
        payload={"membership_type": payload.membership_type},
    )
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def update_membership_loadout_role(
    db: Session,
    event_id: str,
    membership_id: str,
    payload: EventMembershipLoadoutRoleUpdate,
    actor: str,
) -> EventResponse | None:
    event = get_event(db, event_id)
    membership = db.scalar(
        select(EventMembership).where(
            EventMembership.id == membership_id,
            EventMembership.event_id == event_id,
        )
    )
    if event is None or membership is None:
        return None
    membership.loadout_role = payload.loadout_role
    _lifecycle_snapshot(
        db,
        event_type="event.membership.loadout_role.updated",
        entity_type="event_membership",
        entity_id=membership.id,
        actor=actor,
        payload={"loadout_role": payload.loadout_role},
    )
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def update_membership(
    db: Session,
    event_id: str,
    membership_id: str,
    payload: EventMembershipUpdate,
    actor: str,
) -> EventResponse | None:
    event = get_event(db, event_id)
    membership = db.scalar(
        select(EventMembership).where(
            EventMembership.id == membership_id,
            EventMembership.event_id == event_id,
        )
    )
    if event is None or membership is None:
        return None
    _ensure_event_editable(db, event_id)
    user = db.get(User, membership.user_id)
    if user is None:
        raise EventManagementError("Event attendee account was not found")

    email = payload.email.strip().lower()
    duplicate_user = db.scalar(select(User.id).where(User.email == email, User.id != user.id))
    if duplicate_user is not None:
        raise EventManagementError("Another account already uses this email address")

    if payload.membership_type == "vendor":
        event_only_source = f"event-only:{event_id}"
        vendors = db.scalars(
            select(CatalogVendor).where(CatalogVendor.vendor_code.in_(payload.vendor_codes))
        ).all()
        available = {
            vendor.vendor_code
            for vendor in vendors
            if vendor.is_active or vendor.source_file == event_only_source
        }
        if set(payload.vendor_codes) != available:
            raise EventManagementError(
                "One or more selected vendor companies are unavailable for this event"
            )
        if not _vendor_codes_owned_or_alias(db, user, set(payload.vendor_codes)):
            raise EventManagementError(
                "The attendee can only represent vendor accounts assigned in the main portal"
            )

    if payload.membership_type == "franchise_representative":
        from app.models.store import Store

        entity_exists = db.scalar(
            select(Store.id).where(
                Store.entity_code == payload.entity_code,
                Store.is_active.is_(True),
                Store.is_ordering_enabled.is_(True),
            )
        )
        if entity_exists is None:
            raise EventManagementError("Entity is not active for ordering")

    previous = {
        "email": user.email,
        "display_name": user.display_name,
        "membership_type": membership.membership_type,
        "vendor_codes": list(membership.vendor_codes or []),
        "entity_code": membership.entity_code,
        "module_codes": list(membership.module_codes or []),
        "task_scope": membership.task_scope,
        "is_active": membership.is_active,
    }
    user.email = email
    user.display_name = payload.display_name.strip()
    if payload.password:
        user.password_hash = hash_password(payload.password)
        user.password_change_required = True
    membership.membership_type = payload.membership_type
    membership.vendor_codes = (
        list(payload.vendor_codes) if payload.membership_type == "vendor" else []
    )
    membership.vendor_code = (
        payload.vendor_codes[0]
        if payload.membership_type == "vendor" and payload.vendor_codes
        else None
    )
    membership.entity_code = (
        payload.entity_code if payload.membership_type == "franchise_representative" else None
    )
    membership.module_codes = sorted(set(payload.module_codes))
    membership.task_scope = payload.task_scope
    membership.is_active = payload.is_active
    _lifecycle_snapshot(
        db,
        event_type="event.membership.updated",
        entity_type="event_membership",
        entity_id=membership.id,
        actor=actor,
        payload={
            "event_id": event_id,
            "user_id": user.id,
            "previous": previous,
            "current": {
                "email": user.email,
                "display_name": user.display_name,
                "membership_type": membership.membership_type,
                "vendor_codes": membership.vendor_codes,
                "entity_code": membership.entity_code,
                "module_codes": membership.module_codes,
                "task_scope": membership.task_scope,
                "is_active": membership.is_active,
                "password_reset": bool(payload.password),
            },
        },
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise EventManagementError("The attendee update conflicts with an existing record") from exc
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def _vendor_name_key(value: str | None) -> str:
    return "".join(character for character in (value or "").upper() if character.isalnum())


def _vendor_codes_owned_or_alias(db: Session, user: User, requested_codes: set[str]) -> bool:
    owned_codes = {code.upper() for code in vendor_codes_for_user(db, user)}
    unresolved = requested_codes - owned_codes
    if not unresolved:
        return True
    requested_vendors = db.scalars(
        select(CatalogVendor).where(CatalogVendor.vendor_code.in_(unresolved))
    ).all()
    owned_vendors = db.scalars(
        select(CatalogVendor).where(CatalogVendor.vendor_code.in_(owned_codes))
    ).all()
    owned_names = {_vendor_name_key(vendor.name) for vendor in owned_vendors}
    return all(
        any(
            requested_name == owned_name
            or requested_name in owned_name
            or owned_name in requested_name
            for owned_name in owned_names
        )
        for requested_name in (_vendor_name_key(vendor.name) for vendor in requested_vendors)
    )


def list_event_account_directory(db: Session) -> list[EventAccountDirectoryResponse]:
    users = db.scalars(select(User).order_by(User.display_name, User.email)).all()
    return [
        EventAccountDirectoryResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            vendor_codes=vendor_codes_for_user(db, user),
        )
        for user in users
    ]


def _ensure_event_editable(db: Session, event_id: str) -> None:
    if event_operations_are_locked(db, event_id):
        raise EventManagementError(
            "Event configuration is locked because archived events are read-only"
        )


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _query():
    return select(ManagedEvent).options(
        selectinload(ManagedEvent.sub_events),
        selectinload(ManagedEvent.memberships).selectinload(EventMembership.user),
        selectinload(ManagedEvent.memberships).selectinload(
            EventMembership.sub_event_registrations
        ),
        selectinload(ManagedEvent.branding),
        selectinload(ManagedEvent.venue_map),
    )


def event_response(event: ManagedEvent) -> EventResponse:
    return EventResponse(
        **{field: getattr(event, field) for field in EventWrite.model_fields},
        id=event.id,
        created_by=event.created_by,
        created_at=event.created_at,
        cancelled_at=event.cancelled_at,
        cancelled_by=event.cancelled_by,
        cancellation_reason=event.cancellation_reason,
        has_branding=event.branding is not None,
        has_venue_map=event.venue_map is not None,
        sub_events=event.sub_events,
        memberships=[
            EventMembershipResponse(
                id=item.id,
                event_id=item.event_id,
                user_id=item.user_id,
                email=item.user.email,
                display_name=item.user.display_name,
                membership_type=item.membership_type,
                vendor_code=item.vendor_code,
                vendor_codes=item.vendor_codes or ([item.vendor_code] if item.vendor_code else []),
                entity_code=item.entity_code,
                loadout_role=item.loadout_role,
                module_codes=item.module_codes,
                task_scope=item.task_scope,
                is_active=item.is_active,
                sub_event_scope_configured=item.sub_event_scope_configured,
                sub_event_ids=sorted(
                    registration.sub_event_id for registration in item.sub_event_registrations
                ),
                sub_event_roles={
                    registration.sub_event_id: registration.role
                    for registration in item.sub_event_registrations
                },
            )
            for item in item_sorted(event.memberships)
        ],
    )


def item_sorted(items: list[EventMembership]) -> list[EventMembership]:
    return sorted(items, key=lambda item: (item.membership_type, item.user.email))


def _lifecycle_snapshot(
    db: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor: str,
    payload: dict,
) -> None:
    db.add(
        EventSnapshot(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            payload=payload,
        )
    )


def list_active_events(db: Session) -> list[EventResponse]:
    events = (
        db.scalars(
            _query()
            .where(ManagedEvent.status.in_(("draft", "published")))
            .order_by(ManagedEvent.starts_at.desc())
        )
        .unique()
        .all()
    )
    return [event_response(event) for event in events]


def list_archived_events(db: Session) -> list[EventResponse]:
    events = (
        db.scalars(
            _query()
            .where(ManagedEvent.status.in_(("completed", "cancelled")))
            .order_by(ManagedEvent.ends_at.desc())
        )
        .unique()
        .all()
    )
    return [event_response(event) for event in events]


def list_registered_active_events(db: Session, user_id: int) -> list[EventResponse]:
    events = (
        db.scalars(
            _query()
            .join(EventMembership, EventMembership.event_id == ManagedEvent.id)
            .where(
                EventMembership.user_id == user_id,
                EventMembership.is_active.is_(True),
                ManagedEvent.status.in_(("draft", "published")),
            )
            .order_by(ManagedEvent.starts_at.desc())
        )
        .unique()
        .all()
    )
    return [event_response(event) for event in events]


def list_member_events(db: Session, user_id: int) -> list[EventResponse]:
    events = (
        db.scalars(
            _query()
            .join(EventMembership, EventMembership.event_id == ManagedEvent.id)
            .where(
                EventMembership.user_id == user_id,
                EventMembership.is_active.is_(True),
            )
            .order_by(ManagedEvent.starts_at.desc())
        )
        .unique()
        .all()
    )
    responses = []
    for event in events:
        response = event_response(event)
        membership = next(item for item in event.memberships if item.user_id == user_id)
        response = response.model_copy(
            update={
                "memberships": [item for item in response.memberships if item.user_id == user_id]
            }
        )
        if membership.sub_event_scope_configured:
            allowed = {
                registration.sub_event_id for registration in membership.sub_event_registrations
            }
            response = response.model_copy(
                update={"sub_events": [item for item in response.sub_events if item.id in allowed]}
            )
        responses.append(response)
    return responses


def assign_membership_sub_events(
    db: Session,
    event_id: str,
    membership_id: str,
    payload: EventSubEventRegistrationWrite,
    actor: str,
) -> EventResponse | None:
    membership = db.get(EventMembership, membership_id)
    if membership is None or membership.event_id != event_id:
        return None
    _ensure_event_editable(db, event_id)
    requested = set(payload.sub_event_ids)
    valid = set(
        db.scalars(select(ManagedSubEvent.id).where(ManagedSubEvent.event_id == event_id)).all()
    )
    if not requested.issubset(valid):
        raise EventManagementError("One or more sub-events do not belong to this event")
    if not set(payload.roles).issubset(requested):
        raise EventManagementError("Sub-event roles may only be assigned to selected sub-events")
    db.execute(
        delete(EventSubEventRegistration).where(
            EventSubEventRegistration.membership_id == membership_id
        )
    )
    db.add_all(
        EventSubEventRegistration(
            event_id=event_id,
            sub_event_id=sub_event_id,
            membership_id=membership_id,
            assigned_by=actor,
            role=payload.roles.get(sub_event_id),
        )
        for sub_event_id in sorted(requested)
    )
    membership.sub_event_scope_configured = True
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def get_event(db: Session, event_id: str) -> ManagedEvent | None:
    return db.scalar(_query().where(ManagedEvent.id == event_id))


def create_event(db: Session, payload: EventWrite, actor: str) -> EventResponse:
    event = ManagedEvent(**payload.model_dump(), created_by=actor)
    db.add(event)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise EventManagementError("Event slug already exists") from exc
    return event_response(get_event(db, event.id))  # type: ignore[arg-type]


def update_event(db: Session, event_id: str, payload: EventWrite) -> EventResponse | None:
    event = get_event(db, event_id)
    if event is None:
        return None
    _ensure_event_editable(db, event_id)
    for field, value in payload.model_dump().items():
        setattr(event, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise EventManagementError("Event slug already exists") from exc
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def publish_event(db: Session, event_id: str, actor: str) -> EventResponse | None:
    event = get_event(db, event_id)
    if event is None:
        return None
    _ensure_event_editable(db, event_id)
    if event.status in {"completed", "cancelled"}:
        raise EventManagementError("Completed or cancelled events cannot be published")
    if event.status == "published":
        return event_response(event)
    event.status = "published"
    sub_events_published = db.execute(
        update(ManagedSubEvent)
        .where(
            ManagedSubEvent.event_id == event_id,
            ManagedSubEvent.status == "draft",
        )
        .values(status="published")
    ).rowcount
    _lifecycle_snapshot(
        db,
        event_type="event.published",
        entity_type="managed_event",
        entity_id=event.id,
        actor=actor,
        payload={
            "event_name": event.name,
            "previous_status": "draft",
            "sub_events_published": sub_events_published,
        },
    )
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def cancel_event(
    db: Session,
    event_id: str,
    payload: EventCancellationWrite,
    actor: str,
) -> EventResponse | None:
    event = get_event(db, event_id)
    if event is None:
        return None
    _ensure_event_editable(db, event_id)
    if event.status == "completed":
        raise EventManagementError("Completed events must be retained for audit history")
    previous_status = event.status
    cancelled_at = datetime.now(UTC)
    sub_event_restore_state = [
        {"id": item.id, "status": item.status}
        for item in db.scalars(
            select(ManagedSubEvent).where(ManagedSubEvent.event_id == event_id)
        ).all()
    ]
    calendar_restore_state = [
        {"id": item.id, "is_active": item.is_active}
        for item in db.scalars(
            select(EventCalendarEntry).where(EventCalendarEntry.event_id == event_id)
        ).all()
    ]
    presentation_restore_state = [
        {
            "sub_event_id": item.sub_event_id,
            "status": item.status,
            "ordering_status": item.ordering_status,
            "updated_by": item.updated_by,
        }
        for item in db.scalars(
            select(EventPresentationState).where(EventPresentationState.event_id == event_id)
        ).all()
    ]
    poll_restore_state = [
        {
            "id": item.id,
            "status": item.status,
            "closed_at": item.closed_at.isoformat() if item.closed_at else None,
        }
        for item in db.scalars(select(EventPoll).where(EventPoll.event_id == event_id)).all()
    ]
    event.status = "cancelled"
    event.cancelled_at = cancelled_at
    event.cancelled_by = actor
    event.cancellation_reason = payload.reason.strip()
    sub_events_cancelled = db.execute(
        update(ManagedSubEvent)
        .where(
            ManagedSubEvent.event_id == event_id,
            ManagedSubEvent.status != "completed",
        )
        .values(status="cancelled")
    )
    calendar_entries_hidden = db.execute(
        update(EventCalendarEntry)
        .where(
            EventCalendarEntry.event_id == event_id,
            EventCalendarEntry.is_active.is_(True),
        )
        .values(is_active=False)
    ).rowcount
    presentations_ended = db.execute(
        update(EventPresentationState)
        .where(EventPresentationState.event_id == event_id)
        .values(
            status="ended",
            ordering_status="closed",
            updated_by=actor,
        )
    ).rowcount
    polls_closed = db.execute(
        update(EventPoll)
        .where(EventPoll.event_id == event_id, EventPoll.status != "closed")
        .values(status="closed", closed_at=cancelled_at)
    ).rowcount
    _lifecycle_snapshot(
        db,
        event_type="event.cancelled",
        entity_type="managed_event",
        entity_id=event.id,
        actor=actor,
        payload={
            "event_name": event.name,
            "reason": event.cancellation_reason,
            "previous_status": previous_status,
            "sub_events_cancelled": sub_events_cancelled.rowcount,
            "calendar_entries_hidden": calendar_entries_hidden,
            "presentations_ended": presentations_ended,
            "polls_closed": polls_closed,
            "presentation_assets_retained": True,
            "restore_state": {
                "event_status": previous_status,
                "sub_events": sub_event_restore_state,
                "calendar_entries": calendar_restore_state,
                "presentations": presentation_restore_state,
                "polls": poll_restore_state,
            },
        },
    )
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def restore_cancelled_event(
    db: Session,
    event_id: str,
    actor: str,
) -> EventResponse | None:
    event = get_event(db, event_id)
    if event is None:
        return None
    if event.status != "cancelled":
        raise EventManagementError("Only cancelled events can be restored")
    if event_settlement_is_closed(db, event_id):
        raise EventManagementError("Events with closed settlement records cannot be restored")

    cancellation = db.scalar(
        select(EventSnapshot)
        .where(
            EventSnapshot.entity_id == event_id,
            EventSnapshot.entity_type == "managed_event",
            EventSnapshot.event_type == "event.cancelled",
        )
        .order_by(EventSnapshot.created_at.desc(), EventSnapshot.id.desc())
    )
    restore_state = cancellation.payload.get("restore_state") if cancellation else None
    if not isinstance(restore_state, dict):
        raise EventManagementError(
            "This cancellation predates automatic restoration; use a verified backup recovery"
        )

    restored_status = restore_state.get("event_status")
    if restored_status not in {"draft", "published"}:
        raise EventManagementError("The cancellation audit record has an invalid prior status")

    sub_event_states = restore_state.get("sub_events", [])
    calendar_states = restore_state.get("calendar_entries", [])
    presentation_states = restore_state.get("presentations", [])
    poll_states = restore_state.get("polls", [])
    for state_group in (
        sub_event_states,
        calendar_states,
        presentation_states,
        poll_states,
    ):
        if not isinstance(state_group, list):
            raise EventManagementError("The cancellation audit restore data is invalid")

    event.status = restored_status
    event.cancelled_at = None
    event.cancelled_by = None
    event.cancellation_reason = None

    restored_sub_events = 0
    for state in sub_event_states:
        if not isinstance(state, dict):
            continue
        sub_event = db.get(ManagedSubEvent, state.get("id"))
        status = state.get("status")
        if sub_event and sub_event.event_id == event_id and isinstance(status, str):
            sub_event.status = status
            restored_sub_events += 1

    restored_calendar_entries = 0
    for state in calendar_states:
        if not isinstance(state, dict):
            continue
        entry = db.get(EventCalendarEntry, state.get("id"))
        is_active = state.get("is_active")
        if entry and entry.event_id == event_id and isinstance(is_active, bool):
            entry.is_active = is_active
            restored_calendar_entries += 1

    restored_presentations = 0
    for state in presentation_states:
        if not isinstance(state, dict):
            continue
        presentation = db.get(EventPresentationState, state.get("sub_event_id"))
        if presentation is None or presentation.event_id != event_id:
            continue
        status = state.get("status")
        ordering_status = state.get("ordering_status")
        updated_by = state.get("updated_by")
        if all(isinstance(value, str) for value in (status, ordering_status, updated_by)):
            presentation.status = status
            presentation.ordering_status = ordering_status
            presentation.updated_by = updated_by
            restored_presentations += 1

    restored_polls = 0
    for state in poll_states:
        if not isinstance(state, dict):
            continue
        poll = db.get(EventPoll, state.get("id"))
        status = state.get("status")
        if poll is None or poll.event_id != event_id or not isinstance(status, str):
            continue
        closed_at = state.get("closed_at")
        poll.status = status
        poll.closed_at = datetime.fromisoformat(closed_at) if closed_at else None
        restored_polls += 1

    _lifecycle_snapshot(
        db,
        event_type="event.restored",
        entity_type="managed_event",
        entity_id=event.id,
        actor=actor,
        payload={
            "event_name": event.name,
            "restored_status": restored_status,
            "cancellation_snapshot_id": cancellation.id if cancellation else None,
            "sub_events_restored": restored_sub_events,
            "calendar_entries_restored": restored_calendar_entries,
            "presentations_restored": restored_presentations,
            "polls_restored": restored_polls,
        },
    )
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def remove_event(db: Session, event_id: str, actor: str) -> bool:
    event = get_event(db, event_id)
    if event is None:
        return False
    if event.status not in {"draft", "cancelled"}:
        raise EventManagementError("Cancel a published event before permanently removing it")
    if event_settlement_is_closed(db, event_id):
        raise EventManagementError(
            "This event has retained settlement records and cannot be deleted"
        )
    _lifecycle_snapshot(
        db,
        event_type="event.deleted",
        entity_type="managed_event",
        entity_id=event.id,
        actor=actor,
        payload={
            "event_name": event.name,
            "status": event.status,
            "cancellation_reason": event.cancellation_reason,
            "cancelled_by": event.cancelled_by,
            "cancelled_at": event.cancelled_at.isoformat() if event.cancelled_at else None,
            "sub_event_count": len(event.sub_events),
            "membership_count": len(event.memberships),
        },
    )
    db.delete(event)
    try:
        db.flush()
        db.execute(
            delete(CatalogVendor).where(CatalogVendor.source_file == f"event-only:{event_id}")
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise EventManagementError(
            "This event has released purchasing or retained audit records and cannot be deleted"
        ) from exc
    return True


def add_sub_event(db: Session, event_id: str, payload: SubEventWrite) -> EventResponse | None:
    event = get_event(db, event_id)
    if event is None:
        return None
    _ensure_event_editable(db, event_id)
    unknown_modules = sorted(set(payload.module_codes) - EVENT_MODULES.keys())
    if unknown_modules:
        raise EventManagementError(f"Unknown event modules: {', '.join(unknown_modules)}")
    if _utc(payload.starts_at) < _utc(event.starts_at) or _utc(payload.ends_at) > _utc(
        event.ends_at
    ):
        raise EventManagementError("Sub-event must occur within the main event dates")
    values = payload.model_dump()
    values["module_codes"] = sorted(set(payload.module_codes))
    db.add(ManagedSubEvent(event_id=event_id, **values))
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def update_sub_event_modules(
    db: Session, event_id: str, sub_event_id: str, payload: SubEventModulesWrite
) -> EventResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None or sub_event.event_id != event_id:
        return None
    _ensure_event_editable(db, event_id)
    sub_event.module_codes = payload.module_codes
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def update_sub_event(
    db: Session, event_id: str, sub_event_id: str, payload: SubEventWrite
) -> EventResponse | None:
    event = get_event(db, event_id)
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if event is None or sub_event is None or sub_event.event_id != event_id:
        return None
    _ensure_event_editable(db, event_id)
    if _utc(payload.starts_at) < _utc(event.starts_at) or _utc(payload.ends_at) > _utc(
        event.ends_at
    ):
        raise EventManagementError("Sub-event must occur within the main event dates")
    for field, value in payload.model_dump(exclude={"module_codes"}).items():
        setattr(sub_event, field, value)
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def remove_sub_event(
    db: Session,
    event_id: str,
    sub_event_id: str,
    actor: str,
) -> EventResponse | None:
    event = get_event(db, event_id)
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if event is None or sub_event is None or sub_event.event_id != event_id:
        return None
    _ensure_event_editable(db, event_id)
    _lifecycle_snapshot(
        db,
        event_type="event.sub_event.deleted",
        entity_type="managed_sub_event",
        entity_id=sub_event.id,
        actor=actor,
        payload={
            "event_id": event.id,
            "event_name": event.name,
            "sub_event_name": sub_event.name,
            "status": sub_event.status,
            "starts_at": sub_event.starts_at.isoformat(),
            "ends_at": sub_event.ends_at.isoformat(),
        },
    )
    db.delete(sub_event)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise EventManagementError(
            "This sub-event has released purchasing records and cannot be deleted"
        ) from exc
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def add_membership(
    db: Session, event_id: str, payload: EventMembershipCreate
) -> EventResponse | None:
    event = get_event(db, event_id)
    if event is None:
        return None
    _ensure_event_editable(db, event_id)
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    existing_user = user is not None
    if user is None:
        if payload.password is None:
            raise EventManagementError("A password is required for a new event account")
        user = User(
            email=email,
            display_name=payload.display_name.strip(),
            password_hash=hash_password(payload.password),
            vendor_code=(
                payload.vendor_codes[0]
                if payload.membership_type == "vendor" and payload.vendor_codes
                else payload.vendor_code
                if payload.membership_type == "vendor"
                else None
            ),
            is_active=True,
        )
        db.add(user)
        db.flush()
    if payload.membership_type == "vendor":
        event_only_source = f"event-only:{event_id}"
        vendors = db.scalars(
            select(CatalogVendor).where(CatalogVendor.vendor_code.in_(payload.vendor_codes))
        ).all()
        available = {
            vendor.vendor_code
            for vendor in vendors
            if vendor.is_active or vendor.source_file == event_only_source
        }
        if set(payload.vendor_codes) != available:
            raise EventManagementError(
                "One or more selected vendor companies are unavailable for this event"
            )
        if existing_user and not _vendor_codes_owned_or_alias(db, user, set(payload.vendor_codes)):
            raise EventManagementError(
                "The attendee can only represent vendor accounts assigned in the main portal"
            )
        if not existing_user and len(payload.vendor_codes) > 1:
            raise EventManagementError(
                "Create the vendor account assignments in the main portal before "
                "granting multi-vendor event access"
            )
        if user.vendor_code is not None and user.vendor_code not in payload.vendor_codes:
            raise EventManagementError("User belongs to a different main-platform vendor")
    if payload.membership_type == "franchise_representative":
        from app.models.store import Store

        entity_exists = db.scalar(
            select(Store.id).where(
                Store.entity_code == payload.entity_code,
                Store.is_active.is_(True),
                Store.is_ordering_enabled.is_(True),
            )
        )
        if entity_exists is None:
            raise EventManagementError("Entity is not active for ordering")
    existing = db.scalar(
        select(EventMembership.id).where(
            EventMembership.event_id == event_id, EventMembership.user_id == user.id
        )
    )
    if existing is not None:
        raise EventManagementError("User is already assigned to this event")
    db.add(
        EventMembership(
            event_id=event_id,
            user_id=user.id,
            membership_type=payload.membership_type,
            vendor_code=payload.vendor_code if payload.membership_type == "vendor" else None,
            vendor_codes=(
                list(payload.vendor_codes) if payload.membership_type == "vendor" else []
            ),
            entity_code=(
                payload.entity_code
                if payload.membership_type == "franchise_representative"
                else None
            ),
            module_codes=sorted(set(payload.module_codes)),
            task_scope=payload.task_scope,
            is_active=payload.is_active,
        )
    )
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def update_membership_vendors(
    db: Session,
    event_id: str,
    membership_id: str,
    payload: EventVendorMembershipUpdate,
    actor: str,
) -> EventResponse | None:
    membership = db.get(EventMembership, membership_id)
    if membership is None or membership.event_id != event_id:
        return None
    if membership.membership_type != "vendor":
        raise EventManagementError("Only vendor attendees have vendor registrations")
    _ensure_event_editable(db, event_id)
    user = db.get(User, membership.user_id)
    if user is None:
        raise EventManagementError("Vendor attendee account was not found")
    requested = {code.strip().upper() for code in payload.vendor_codes if code.strip()}
    if not _vendor_codes_owned_or_alias(db, user, requested):
        raise EventManagementError(
            "The attendee can only represent vendor accounts assigned in the main portal"
        )
    registered = set(
        db.scalars(
            select(EventVendorBooth.vendor_code).where(
                EventVendorBooth.event_id == event_id,
                EventVendorBooth.vendor_code.is_not(None),
            )
        ).all()
    )
    registered = {code.strip().upper() for code in registered if code}
    if not requested.issubset(registered):
        raise EventManagementError(
            "Each selected vendor must have a registered booth in this event"
        )
    previous = list(membership.vendor_codes or [])
    membership.vendor_codes = sorted(requested)
    membership.vendor_code = sorted(requested)[0]
    db.add(
        EventSnapshot(
            event_type="event.membership.vendor_access.updated",
            entity_type="event_membership",
            entity_id=membership.id,
            actor=actor,
            payload={
                "event_id": event_id,
                "user_id": membership.user_id,
                "previous_vendor_codes": previous,
                "vendor_codes": sorted(requested),
            },
        )
    )
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def save_branding(
    db: Session,
    event_id: str,
    filename: str,
    content_type: str,
    content: bytes,
    actor: str,
) -> EventResponse | None:
    event = get_event(db, event_id)
    if event is None:
        return None
    _ensure_event_editable(db, event_id)
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise EventManagementError("Branding image must be PNG, JPEG, or WebP")
    if not content or len(content) > 5 * 1024 * 1024:
        raise EventManagementError("Branding image must be between 1 byte and 5 MB")
    if not content_matches_declared_type(content, content_type):
        raise EventManagementError("Branding image content does not match its declared type")
    asset = db.get(EventBrandingAsset, event_id)
    if asset is None:
        asset = EventBrandingAsset(event_id=event_id)
        db.add(asset)
    asset.filename = filename[:255]
    asset.content_type = content_type
    asset.content = content
    asset.uploaded_by = actor
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]


def save_venue_map(
    db: Session,
    event_id: str,
    filename: str,
    content_type: str,
    content: bytes,
    actor: str,
) -> EventResponse | None:
    event = get_event(db, event_id)
    if event is None:
        return None
    _ensure_event_editable(db, event_id)
    allowed = {"application/pdf", "image/png", "image/jpeg", "image/webp"}
    if content_type not in allowed:
        raise EventManagementError("Venue map must be a PDF, PNG, JPEG, or WebP file")
    if not content or len(content) > 10 * 1024 * 1024:
        raise EventManagementError("Venue map must be between 1 byte and 10 MB")
    if not content_matches_declared_type(content, content_type):
        raise EventManagementError("Venue map content does not match its declared type")
    asset = db.get(EventVenueMapAsset, event_id)
    if asset is None:
        asset = EventVenueMapAsset(event_id=event_id)
        db.add(asset)
    asset.filename = filename[:255]
    asset.content_type = content_type
    asset.content = content
    asset.uploaded_by = actor
    db.commit()
    return event_response(get_event(db, event_id))  # type: ignore[arg-type]
