from datetime import UTC, datetime
from io import BytesIO
from xml.sax.saxutils import escape  # nosec B406

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.catalog import CatalogVendor
from app.models.event_management import (
    EventMembership,
    ManagedEvent,
    StoreLoadoutAssignment,
    StoreLoadoutAuditLog,
    StoreLoadoutEvent,
    StoreLoadoutItem,
    StoreLoadoutItemAttachment,
    StoreLoadoutItemCheckin,
    StoreLoadoutSignoff,
    VendorHallBooth,
    VendorHallInventoryItem,
    VendorHallItemCheckin,
)
from app.models.identity import User
from app.models.notification import NotificationEvent
from app.models.store import Store
from app.schemas.store_loadout import (
    StoreLoadoutAssignmentResponse,
    StoreLoadoutAssignmentWrite,
    StoreLoadoutEventResponse,
    StoreLoadoutEventWrite,
    StoreLoadoutFinalReviewWrite,
    StoreLoadoutItemCheckinResponse,
    StoreLoadoutItemCheckinWrite,
    StoreLoadoutItemResponse,
    StoreLoadoutReassignmentWrite,
    StoreLoadoutSignoffResponse,
    StoreLoadoutSignoffWrite,
    StoreLoadoutSummaryResponse,
    StoreLoadoutTeamSummary,
    StoreLoadoutTeamWrite,
    StoreLoadoutVehicleStatusWrite,
)
from app.services.event_access_service import event_operations_are_locked
from app.services.upload_validation import content_matches_declared_type


class StoreLoadoutError(ValueError):
    pass


class StoreLoadoutAccessError(PermissionError):
    pass


MAX_LOADOUT_ATTACHMENT_BYTES = 8 * 1024 * 1024
LOADOUT_ATTACHMENT_TYPES = {"photo", "other"}
LOADOUT_ATTACHMENT_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _assert_event_open(db: Session, event_id: str) -> None:
    if event_operations_are_locked(db, event_id):
        raise StoreLoadoutError(
            "Store loadout is locked because the event is cancelled or settlement is closed"
        )


def attach_store_loadout_item_file(
    db: Session,
    assignment_id: str,
    item_id: str,
    attachment_type: str,
    filename: str,
    content_type: str,
    content: bytes,
    user: User,
) -> dict[str, object] | None:
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is None:
        return None
    _assert_event_open(db, assignment.event_id)
    if not _assignment_visible_to_user(db, assignment, user):
        raise StoreLoadoutAccessError("Store loadout assignment is outside this user's scope")
    item = db.get(StoreLoadoutItem, item_id)
    if item is None or item.assignment_id != assignment.id:
        return None
    if attachment_type not in LOADOUT_ATTACHMENT_TYPES:
        raise StoreLoadoutError("Attachment type must be photo or other")
    if content_type not in LOADOUT_ATTACHMENT_CONTENT_TYPES:
        raise StoreLoadoutError("Loadout evidence must be JPEG, PNG, or WebP")
    if not content or len(content) > MAX_LOADOUT_ATTACHMENT_BYTES:
        raise StoreLoadoutError("Loadout evidence must be between 1 byte and 8 MB")
    if not content_matches_declared_type(content, content_type):
        raise StoreLoadoutError("Attachment content does not match its declared type")
    attachment = StoreLoadoutItemAttachment(
        event_id=assignment.event_id,
        assignment_id=assignment.id,
        loadout_item_id=item.id,
        attachment_type=attachment_type,
        filename=filename[:255],
        content_type=content_type,
        content=content,
        uploaded_by=user.email,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return {
        "id": attachment.id,
        "assignment_id": attachment.assignment_id,
        "loadout_item_id": attachment.loadout_item_id,
        "attachment_type": attachment.attachment_type,
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "uploaded_by": attachment.uploaded_by,
        "created_at": attachment.created_at,
    }


def store_loadout_item_attachment_content(
    db: Session,
    assignment_id: str,
    item_id: str,
    attachment_id: str,
    user: User,
) -> tuple[str, str, bytes] | None:
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is None:
        return None
    if not _assignment_visible_to_user(db, assignment, user):
        raise StoreLoadoutAccessError("Store loadout assignment is outside this user's scope")
    attachment = db.get(StoreLoadoutItemAttachment, attachment_id)
    if (
        attachment is None
        or attachment.assignment_id != assignment.id
        or attachment.loadout_item_id != item_id
    ):
        return None
    return attachment.filename, attachment.content_type, attachment.content


EXCEPTION_ITEM_STATUSES = {"damaged", "missing", "quantity_mismatch", "substituted"}
ACCOUNTED_ITEM_STATUSES = {
    "found",
    "damaged",
    "missing",
    "quantity_mismatch",
    "substituted",
    "removed",
    "signed_off",
}
STORE_LOADOUT_EXPORTS = {
    "master",
    "packing-lists",
    "damaged-items",
    "missing-items",
    "departure-schedule",
    "audit-log",
}


def _vehicle_sort_key(label: str) -> tuple[int, int, str]:
    normalized = label.strip().lower()
    kind = 0 if normalized.startswith("truck") else 1 if normalized.startswith("van") else 2
    digits = "".join(character for character in normalized if character.isdigit())
    return kind, int(digits or 999), normalized


def ordered_vehicle_labels(labels: list[str] | None) -> list[str]:
    unique: dict[str, str] = {}
    for raw_label in labels or []:
        label = raw_label.strip()
        if label:
            unique.setdefault(label.casefold(), label)
    return sorted(unique.values(), key=_vehicle_sort_key) or ["Truck 1"]


def auto_order_store_loadout(
    db: Session,
    event_id: str,
    actor: str,
) -> list[StoreLoadoutAssignmentResponse] | None:
    _assert_event_open(db, event_id)
    assignments = db.scalars(
        select(StoreLoadoutAssignment).where(
            StoreLoadoutAssignment.event_id == event_id,
            StoreLoadoutAssignment.status != "released_from_venue",
        )
    ).all()
    if db.get(ManagedEvent, event_id) is None:
        return None

    def distance_key(item: StoreLoadoutAssignment) -> tuple[bool, float, str]:
        return (
            item.distance_miles is None,
            -(float(item.distance_miles) if item.distance_miles is not None else 0),
            item.store_number,
        )

    grouped: dict[str, list[StoreLoadoutAssignment]] = {}
    for assignment in assignments:
        grouped.setdefault(assignment.team_name or "__unassigned__", []).append(assignment)
    ordered_groups = sorted(
        grouped.items(),
        key=lambda pair: (
            pair[0] == "__unassigned__",
            min(distance_key(item) for item in pair[1]),
        ),
    )
    ordered = [
        item
        for _team_name, team_assignments in ordered_groups
        for item in sorted(team_assignments, key=distance_key)
    ]
    for priority, assignment in enumerate(ordered, start=1):
        assignment.pickup_priority = priority
        assignment.vehicle_labels = ordered_vehicle_labels(assignment.vehicle_labels)
    db.commit()
    for assignment in ordered:
        _audit(
            db,
            event_id,
            assignment.store_loadout_event_id,
            assignment.id,
            None,
            "store_loadout.order.optimized",
            actor,
            {
                "pickup_priority": assignment.pickup_priority,
                "distance_miles": str(assignment.distance_miles or ""),
            },
        )
    return _assignment_responses(db, ordered, include_items=True)


def configure_store_loadout(
    db: Session,
    event_id: str,
    payload: StoreLoadoutEventWrite,
    actor: str,
) -> StoreLoadoutEventResponse | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    _assert_event_open(db, event_id)
    loadout = get_store_loadout(db, event_id)
    if loadout is None:
        loadout = StoreLoadoutEvent(event_id=event_id, created_by=actor)
        db.add(loadout)
    for field, value in payload.model_dump().items():
        setattr(loadout, field, value)
    db.commit()
    db.refresh(loadout)
    _audit(
        db,
        event_id,
        loadout.id,
        None,
        None,
        "store_loadout.configured",
        actor,
        payload.model_dump(),
    )
    return _event_response(db, loadout)


def get_store_loadout(db: Session, event_id: str) -> StoreLoadoutEvent | None:
    return db.scalar(select(StoreLoadoutEvent).where(StoreLoadoutEvent.event_id == event_id))


def store_loadout_window_open(
    db: Session,
    event_id: str,
    now: datetime | None = None,
) -> bool:
    loadout = get_store_loadout(db, event_id)
    if loadout is None or loadout.status != "open":
        return False
    current = now or datetime.now(UTC)
    if loadout.opens_at:
        opens_at = (
            loadout.opens_at if loadout.opens_at.tzinfo else loadout.opens_at.replace(tzinfo=UTC)
        )
        if current < opens_at:
            return False
    if loadout.loadout_deadline:
        deadline = (
            loadout.loadout_deadline
            if loadout.loadout_deadline.tzinfo
            else loadout.loadout_deadline.replace(tzinfo=UTC)
        )
        if current > deadline:
            return False
    return True


def create_store_loadout_assignment(
    db: Session,
    event_id: str,
    payload: StoreLoadoutAssignmentWrite,
    actor: str,
) -> StoreLoadoutAssignmentResponse | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    _assert_event_open(db, event_id)
    loadout = get_store_loadout(db, event_id)
    if loadout is None:
        loadout = StoreLoadoutEvent(event_id=event_id, created_by=actor)
        db.add(loadout)
        db.flush()
    store = db.scalar(select(Store).where(Store.store_number == payload.store_number))
    entity_code = payload.entity_code or (store.entity_code if store else None)
    vehicle_labels = [label.strip() for label in (payload.vehicle_labels or []) if label.strip()]
    for item_payload in payload.items:
        if item_payload.vehicle_label and item_payload.vehicle_label.strip():
            vehicle_labels.append(item_payload.vehicle_label.strip())
    vehicle_labels = ordered_vehicle_labels(vehicle_labels)
    assignment = StoreLoadoutAssignment(
        store_loadout_event_id=loadout.id,
        event_id=event_id,
        store_number=payload.store_number,
        entity_code=entity_code,
        pickup_priority=payload.pickup_priority,
        loadout_zone=payload.loadout_zone or loadout.default_loadout_zone,
        distance_miles=payload.distance_miles,
        estimated_drive_minutes=payload.estimated_drive_minutes,
        recommended_departure_at=payload.recommended_departure_at,
        notes=payload.notes,
        vehicle_labels=vehicle_labels,
        vehicle_statuses={label: "expected" for label in vehicle_labels},
        assigned_by=actor,
    )
    db.add(assignment)
    db.flush()
    for item_payload in payload.items:
        source_item = db.get(VendorHallInventoryItem, item_payload.vendor_hall_inventory_item_id)
        if source_item is None or source_item.event_id != event_id:
            raise StoreLoadoutError("Assigned inventory item does not belong to this event")
        if source_item.status == "removed":
            raise StoreLoadoutError("Removed inventory cannot be assigned to a store")
        assigned_quantity = _assigned_quantity(db, source_item.id)
        if assigned_quantity + item_payload.quantity_assigned > source_item.quantity_expected:
            raise StoreLoadoutError("Assigned quantity exceeds available vendor hall quantity")
        booth = db.get(VendorHallBooth, source_item.vendor_hall_booth_id)
        if booth is None:
            raise StoreLoadoutError("Assigned inventory item is missing its booth")
        latest_checkin = db.scalar(
            select(VendorHallItemCheckin)
            .where(VendorHallItemCheckin.inventory_item_id == source_item.id)
            .order_by(desc(VendorHallItemCheckin.checked_at))
            .limit(1)
        )
        prior_damage_note = (
            latest_checkin.damage_notes or latest_checkin.exception_notes
            if latest_checkin is not None
            else None
        )
        db.add(
            StoreLoadoutItem(
                assignment_id=assignment.id,
                event_id=event_id,
                vendor_hall_booth_id=booth.id,
                vendor_hall_inventory_item_id=source_item.id,
                vendor_code=source_item.vendor_code,
                booth_number=booth.booth_number,
                item_name=source_item.item_name,
                model_number=source_item.model_number,
                serial_number=source_item.serial_number,
                quantity_assigned=item_payload.quantity_assigned,
                condition=source_item.condition,
                notes=item_payload.notes or source_item.notes or source_item.vendor_notes,
                damage_notes=prior_damage_note
                or (
                    source_item.staff_notes or source_item.vendor_notes
                    if source_item.status == "damaged"
                    else None
                ),
                vehicle_label=item_payload.vehicle_label,
            )
        )
    db.commit()
    db.refresh(assignment)
    _audit(
        db,
        event_id,
        loadout.id,
        assignment.id,
        None,
        "store_loadout.assignment.created",
        actor,
        {"store_number": assignment.store_number, "item_count": len(payload.items)},
    )
    return _assignment_response(db, assignment, include_items=True)


def list_store_loadout_assignments(
    db: Session,
    event_id: str,
) -> list[StoreLoadoutAssignmentResponse] | None:
    if db.get(ManagedEvent, event_id) is None:
        return None
    assignments = db.scalars(
        select(StoreLoadoutAssignment)
        .where(StoreLoadoutAssignment.event_id == event_id)
        .order_by(StoreLoadoutAssignment.pickup_priority, StoreLoadoutAssignment.store_number)
    ).all()
    return _assignment_responses(db, assignments, include_items=True)


def reassign_store_loadout_inventory(
    db: Session,
    assignment_id: str,
    payload: StoreLoadoutReassignmentWrite,
    actor: str,
) -> StoreLoadoutAssignmentResponse | None:
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is None:
        return None
    _assert_event_open(db, assignment.event_id)
    actor_user = db.scalar(select(User).where(User.email == actor))
    if actor_user is None or not _has_loadout_manager_access(db, actor_user, assignment.event_id):
        raise StoreLoadoutAccessError("Store loadout reassignment requires manager access")
    if (
        assignment.final_review_completed_at is not None
        or assignment.signed_at
        or assignment.released_at
    ):
        raise StoreLoadoutError("Inventory cannot be reassigned after final review is complete")
    existing_items = _assignment_items(db, assignment.id)
    for item in existing_items:
        db.delete(item)
    db.flush()
    vehicle_labels = [label.strip() for label in (payload.vehicle_labels or []) if label.strip()]
    for item_payload in payload.items:
        source_item = db.get(VendorHallInventoryItem, item_payload.vendor_hall_inventory_item_id)
        if source_item is None or source_item.event_id != assignment.event_id:
            raise StoreLoadoutError("Assigned inventory item does not belong to this event")
        if source_item.status == "removed":
            raise StoreLoadoutError("Removed inventory cannot be assigned to a store")
        assigned_quantity = _assigned_quantity(db, source_item.id)
        if assigned_quantity + item_payload.quantity_assigned > source_item.quantity_expected:
            raise StoreLoadoutError("Assigned quantity exceeds available vendor hall quantity")
        booth = db.get(VendorHallBooth, source_item.vendor_hall_booth_id)
        if booth is None:
            raise StoreLoadoutError("Assigned inventory item is missing its booth")
        label = item_payload.vehicle_label.strip() if item_payload.vehicle_label else None
        if label:
            vehicle_labels.append(label)
        db.add(
            StoreLoadoutItem(
                assignment_id=assignment.id,
                event_id=assignment.event_id,
                vendor_hall_booth_id=booth.id,
                vendor_hall_inventory_item_id=source_item.id,
                vendor_code=source_item.vendor_code,
                booth_number=booth.booth_number,
                item_name=source_item.item_name,
                model_number=source_item.model_number,
                serial_number=source_item.serial_number,
                quantity_assigned=item_payload.quantity_assigned,
                condition=source_item.condition,
                notes=item_payload.notes,
                vehicle_label=label,
            )
        )
    assignment.vehicle_labels = ordered_vehicle_labels(vehicle_labels)
    assignment.vehicle_statuses = {label: "expected" for label in assignment.vehicle_labels}
    assignment.notes = payload.notes
    assignment.status = "not_started"
    assignment.final_review_requested_at = None
    assignment.final_review_requested_by = None
    assignment.final_review_notes = None
    db.commit()
    db.refresh(assignment)
    _audit(
        db,
        assignment.event_id,
        assignment.store_loadout_event_id,
        assignment.id,
        None,
        "store_loadout.assignment.reassigned",
        actor,
        {"store_number": assignment.store_number, "item_count": len(payload.items)},
    )
    return _assignment_response(db, assignment, include_items=True)


def my_store_loadout_assignments(db: Session, user: User) -> list[StoreLoadoutAssignmentResponse]:
    assignments = db.scalars(
        select(StoreLoadoutAssignment).order_by(
            StoreLoadoutAssignment.recommended_departure_at,
            StoreLoadoutAssignment.pickup_priority,
        )
    ).all()
    visible_assignments = [
        assignment
        for assignment in assignments
        if _assignment_visible_to_user(db, assignment, user)
    ]
    if not any(
        _has_loadout_manager_access(db, user, assignment.event_id)
        for assignment in visible_assignments
    ):
        visible_assignments = _dock_phase_assignments(visible_assignments, user)
    return _assignment_responses(db, visible_assignments, include_items=True)


def checkin_store_loadout_item(
    db: Session,
    assignment_id: str,
    item_id: str,
    payload: StoreLoadoutItemCheckinWrite,
    user: User,
) -> StoreLoadoutAssignmentResponse | None:
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is None:
        return None
    _assert_event_open(db, assignment.event_id)
    if not _assignment_visible_to_user(db, assignment, user):
        raise StoreLoadoutAccessError("Store loadout assignment is outside this user's scope")
    item = db.get(StoreLoadoutItem, item_id)
    if item is None or item.assignment_id != assignment.id:
        return None
    item.status = _derive_item_status(item.quantity_assigned, payload)
    item.quantity_found = payload.quantity_found
    item.damage_notes = payload.damage_notes
    item.missing_notes = payload.missing_notes
    checkin = StoreLoadoutItemCheckin(
        loadout_item_id=item.id,
        assignment_id=assignment.id,
        status=item.status,
        quantity_found=item.quantity_found,
        damage_notes=item.damage_notes,
        missing_notes=item.missing_notes,
        checked_by=user.email,
    )
    db.add(checkin)
    db.flush()
    _refresh_assignment_status(db, assignment)
    db.commit()
    db.refresh(assignment)
    _audit(
        db,
        assignment.event_id,
        assignment.store_loadout_event_id,
        assignment.id,
        item.id,
        "store_loadout.item.checked_in",
        user.email,
        {
            "status": item.status,
            "quantity_found": item.quantity_found,
            "damage_notes": item.damage_notes,
            "missing_notes": item.missing_notes,
        },
    )
    return _assignment_response(db, assignment, include_items=True)


def mark_store_loadout_assignment_ready(
    db: Session,
    assignment_id: str,
    user: User,
) -> StoreLoadoutAssignmentResponse | None:
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is None:
        return None
    _assert_event_open(db, assignment.event_id)
    if not _assignment_visible_to_user(db, assignment, user):
        raise StoreLoadoutAccessError("Store loadout assignment is outside this user's scope")
    items = _assignment_items(db, assignment.id)
    if not items:
        raise StoreLoadoutError("Assignment has no loadout items")
    if any(item.status == "assigned" for item in items):
        raise StoreLoadoutError("Every assigned item must be checked before final review")
    assignment.status = "ready_for_final_review"
    assignment.final_review_requested_at = datetime.now(UTC)
    assignment.final_review_requested_by = user.email
    db.commit()
    db.refresh(assignment)
    _audit(
        db,
        assignment.event_id,
        assignment.store_loadout_event_id,
        assignment.id,
        None,
        "store_loadout.assignment.ready_for_review",
        user.email,
        {"item_count": len(items)},
    )
    return _assignment_response(db, assignment, include_items=True)


def assign_store_loadout_team(
    db: Session,
    assignment_id: str,
    payload: StoreLoadoutTeamWrite,
    user: User,
) -> StoreLoadoutAssignmentResponse | None:
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is None:
        return None
    _assert_event_open(db, assignment.event_id)
    if not _has_loadout_manager_access(db, user, assignment.event_id):
        raise StoreLoadoutAccessError("Store loadout team assignment requires manager access")
    assignment.team_name = payload.team_name
    assignment.team_member_emails = payload.team_member_emails
    assignment.team_lead_emails = payload.team_lead_emails
    assignment.vehicle_labels = ordered_vehicle_labels(payload.vehicle_labels)
    assignment.vehicle_statuses = {
        label: (assignment.vehicle_statuses or {}).get(label, "expected")
        for label in assignment.vehicle_labels
    }
    db.commit()
    db.refresh(assignment)
    _audit(
        db,
        assignment.event_id,
        assignment.store_loadout_event_id,
        assignment.id,
        None,
        "store_loadout.team.assigned",
        user.email,
        {
            "team_name": assignment.team_name,
            "team_member_emails": assignment.team_member_emails,
            "team_lead_emails": assignment.team_lead_emails,
        },
    )
    return _assignment_response(db, assignment, include_items=True)


def complete_store_loadout_final_review(
    db: Session,
    assignment_id: str,
    payload: StoreLoadoutFinalReviewWrite,
    user: User,
) -> StoreLoadoutAssignmentResponse | None:
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is None:
        return None
    _assert_event_open(db, assignment.event_id)
    is_manager = _has_loadout_manager_access(db, user, assignment.event_id)
    is_team_lead = user.email in (assignment.team_lead_emails or [])
    if not is_manager and not is_team_lead:
        raise StoreLoadoutAccessError(
            "Store loadout final review requires manager or team lead access"
        )
    if assignment.status != "ready_for_final_review":
        raise StoreLoadoutError("Assignment must be ready for final review before staff review")
    items = _assignment_items(db, assignment.id)
    if not items:
        raise StoreLoadoutError("Assignment has no loadout items")
    if any(item.status == "assigned" for item in items):
        raise StoreLoadoutError("Every assigned item must be checked before final review")
    was_already_reviewed = assignment.final_review_completed_at is not None
    reviewed_at = datetime.now(UTC)
    assignment.final_review_completed_at = reviewed_at
    assignment.final_review_completed_by = user.email
    assignment.final_review_notes = payload.notes
    if assignment.team_name:
        team_assignments = db.scalars(
            select(StoreLoadoutAssignment).where(
                StoreLoadoutAssignment.store_loadout_event_id == assignment.store_loadout_event_id,
                StoreLoadoutAssignment.team_name == assignment.team_name,
            )
        ).all()
        if (
            not was_already_reviewed
            and team_assignments
            and all(item.final_review_completed_at is not None for item in team_assignments)
        ):
            loadout = db.get(StoreLoadoutEvent, assignment.store_loadout_event_id)
            next_store = min(
                (item for item in team_assignments if item.status != "released_from_venue"),
                key=lambda item: item.pickup_priority,
                default=None,
            )
            if loadout and loadout.dock_master_email:
                db.add(
                    NotificationEvent(
                        template_code="STORE_LOADOUT_TEAM_READY",
                        workflow_code="EVENTS",
                        event_type="store_loadout.team_ready",
                        entity_type="store_loadout_event",
                        entity_id=loadout.id,
                        actor=user.email,
                        channel="in_app",
                        recipient_strategy="static_recipients",
                        resolved_recipients=[loadout.dock_master_email],
                        subject=f"Loadout team ready: {assignment.team_name}",
                        body=(
                            f"Team {assignment.team_name} completed final review for all "
                            f"{len(team_assignments)} stores and is ready to load."
                        ),
                        status="queued",
                    )
                )
            if next_store:
                for lead_email in next_store.team_lead_emails or []:
                    db.add(
                        NotificationEvent(
                            template_code="STORE_LOADOUT_FIRST_TRUCK",
                            workflow_code="EVENTS",
                            event_type="store_loadout.first_truck_ready",
                            entity_type="store_loadout_assignment",
                            entity_id=next_store.id,
                            actor=user.email,
                            channel="in_app",
                            recipient_strategy="static_recipients",
                            resolved_recipients=[lead_email],
                            subject=f"Bring Store {next_store.store_number} to the dock",
                            body=(
                                f"Team {assignment.team_name} is cleared. Store "
                                f"{next_store.store_number} is first in the loadout order. "
                                "Call vehicles in order: "
                                f"{', '.join(ordered_vehicle_labels(next_store.vehicle_labels))}."
                            ),
                            status="queued",
                        )
                    )
    db.commit()
    db.refresh(assignment)
    _audit(
        db,
        assignment.event_id,
        assignment.store_loadout_event_id,
        assignment.id,
        None,
        "store_loadout.assignment.final_review_completed",
        user.email,
        {
            "reviewed_at": reviewed_at.isoformat(),
            "notes": payload.notes,
            "item_count": len(items),
        },
    )
    return _assignment_response(db, assignment, include_items=True)


def sign_store_loadout_assignment(
    db: Session,
    assignment_id: str,
    payload: StoreLoadoutSignoffWrite,
    user: User,
) -> StoreLoadoutAssignmentResponse | None:
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is None:
        return None
    _assert_event_open(db, assignment.event_id)
    if not _assignment_visible_to_user(db, assignment, user):
        raise StoreLoadoutAccessError("Store loadout assignment is outside this user's scope")
    items = _assignment_items(db, assignment.id)
    if not items:
        raise StoreLoadoutError("Assignment has no loadout items")
    if any(item.status == "assigned" for item in items):
        raise StoreLoadoutError("Every assigned item must be checked before sign-off")
    if assignment.final_review_completed_at is None:
        raise StoreLoadoutError("Event staff final review must be completed before sign-off")
    signed_at = datetime.now(UTC)
    signoff = StoreLoadoutSignoff(
        assignment_id=assignment.id,
        signer_name=payload.signer_name,
        signer_email=payload.signer_email,
        signature_text=payload.signature_text,
        exception_summary=payload.exception_summary,
        signed_at=signed_at,
    )
    db.add(signoff)
    for item in items:
        if item.status not in EXCEPTION_ITEM_STATUSES:
            item.status = "signed_off"
    assignment.status = "signed_complete"
    assignment.signed_at = signed_at
    assignment.signed_by = user.email
    db.commit()
    db.refresh(assignment)
    _audit(
        db,
        assignment.event_id,
        assignment.store_loadout_event_id,
        assignment.id,
        None,
        "store_loadout.assignment.signed",
        user.email,
        {
            "signer_name": payload.signer_name,
            "signer_email": payload.signer_email,
            "exception_summary": payload.exception_summary,
        },
    )
    return _assignment_response(db, assignment, include_items=True)


def release_store_loadout_assignment(
    db: Session,
    assignment_id: str,
    user: User,
) -> StoreLoadoutAssignmentResponse | None:
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is None:
        return None
    _assert_event_open(db, assignment.event_id)
    if not _has_loadout_manager_access(db, user, assignment.event_id):
        raise StoreLoadoutAccessError("Store loadout release requires manager access")
    if assignment.status != "signed_complete":
        raise StoreLoadoutError("Assignment must be signed before venue release")
    # Preserve the legacy manager release action as an emergency override. The
    # normal dock workflow uses the vehicle-status endpoint, which enforces the
    # truck/van sequence and notifies the team lead after each departure.
    labels = ordered_vehicle_labels(assignment.vehicle_labels)
    if labels:
        assignment.vehicle_statuses = {label: "departed" for label in labels}
    if assignment.team_name:
        team_assignments = db.scalars(
            select(StoreLoadoutAssignment).where(
                StoreLoadoutAssignment.store_loadout_event_id == assignment.store_loadout_event_id,
                StoreLoadoutAssignment.team_name == assignment.team_name,
            )
        ).all()
        incomplete_review = next(
            (
                candidate
                for candidate in team_assignments
                if candidate.final_review_completed_at is None
                or (
                    candidate.status not in {"signed_complete", "released_from_venue"}
                    and candidate.final_review_completed_at is None
                )
            ),
            None,
        )
        if incomplete_review is not None:
            raise StoreLoadoutError(
                f"Team {assignment.team_name} cannot load until store "
                f"{incomplete_review.store_number} completes final review"
            )
        earlier = db.scalar(
            select(StoreLoadoutAssignment).where(
                StoreLoadoutAssignment.store_loadout_event_id == assignment.store_loadout_event_id,
                StoreLoadoutAssignment.team_name == assignment.team_name,
                StoreLoadoutAssignment.pickup_priority < assignment.pickup_priority,
                StoreLoadoutAssignment.status != "released_from_venue",
            )
        )
        if earlier is not None:
            raise StoreLoadoutError(
                f"Store {earlier.store_number} must depart before store {assignment.store_number}"
            )
    assignment.status = "released_from_venue"
    assignment.released_at = datetime.now(UTC)
    assignment.released_by = user.email
    loadout = db.get(StoreLoadoutEvent, assignment.store_loadout_event_id)
    team_next = None
    if assignment.team_name:
        team_next = db.scalar(
            select(StoreLoadoutAssignment)
            .where(
                StoreLoadoutAssignment.store_loadout_event_id == assignment.store_loadout_event_id,
                StoreLoadoutAssignment.team_name == assignment.team_name,
                StoreLoadoutAssignment.status == "signed_complete",
            )
            .order_by(StoreLoadoutAssignment.pickup_priority)
        )
    if team_next:
        for lead_email in team_next.team_lead_emails or []:
            db.add(
                NotificationEvent(
                    template_code="STORE_LOADOUT_NEXT_TRUCK",
                    workflow_code="EVENTS",
                    event_type="store_loadout.next_truck",
                    entity_type="store_loadout_assignment",
                    entity_id=team_next.id,
                    actor=user.email,
                    channel="in_app",
                    recipient_strategy="static_recipients",
                    resolved_recipients=[lead_email],
                    subject=f"Next loadout truck: Store {team_next.store_number}",
                    body=(
                        f"Store {team_next.store_number} is next for team "
                        f"{team_next.team_name or 'loadout'}. Call vehicles in order: "
                        f"{', '.join(ordered_vehicle_labels(team_next.vehicle_labels))}."
                    ),
                    status="queued",
                )
            )
    if loadout:
        remaining = db.scalar(
            select(StoreLoadoutAssignment.id).where(
                StoreLoadoutAssignment.store_loadout_event_id == loadout.id,
                StoreLoadoutAssignment.status != "released_from_venue",
            )
        )
        if remaining is None:
            loadout.status = "closed"
            loadout.completed_at = assignment.released_at
    db.commit()
    db.refresh(assignment)
    _audit(
        db,
        assignment.event_id,
        assignment.store_loadout_event_id,
        assignment.id,
        None,
        "store_loadout.assignment.released",
        user.email,
        {"released_at": assignment.released_at.isoformat() if assignment.released_at else None},
    )
    return _assignment_response(db, assignment, include_items=True)


def update_store_loadout_vehicle_status(
    db: Session,
    assignment_id: str,
    vehicle_label: str,
    payload: StoreLoadoutVehicleStatusWrite,
    user: User,
) -> StoreLoadoutAssignmentResponse | None:
    assignment = db.get(StoreLoadoutAssignment, assignment_id)
    if assignment is None:
        return None
    _assert_event_open(db, assignment.event_id)
    if not _has_loadout_manager_access(db, user, assignment.event_id):
        raise StoreLoadoutAccessError("Vehicle departure requires dock manager access")
    labels = ordered_vehicle_labels(assignment.vehicle_labels)
    raw_statuses = assignment.vehicle_statuses or {}
    normalized_statuses = {
        label: next(
            (
                status
                for existing_label, status in raw_statuses.items()
                if existing_label.casefold() == label.casefold()
            ),
            "expected",
        )
        for label in labels
    }
    assignment.vehicle_labels = labels
    assignment.vehicle_statuses = normalized_statuses
    label = vehicle_label.strip()
    if label not in labels:
        raise StoreLoadoutError("Vehicle is not listed on this store assignment")
    if payload.status == "departed":
        if assignment.status != "signed_complete" and assignment.final_review_completed_at is None:
            raise StoreLoadoutError("Store must be signed complete before a vehicle departs")
        statuses = dict(assignment.vehicle_statuses or {})
        position = labels.index(label)
        if any(statuses[name] != "departed" for name in labels[:position]):
            raise StoreLoadoutError("Vehicles must depart in the listed truck/van order")
        statuses[label] = "departed"
        assignment.vehicle_statuses = statuses
        if all(status == "departed" for status in statuses.values()):
            return release_store_loadout_assignment(db, assignment_id, user)
        next_vehicle = next(name for name in labels[position + 1 :] if statuses[name] != "departed")
        for lead_email in assignment.team_lead_emails or []:
            db.add(
                NotificationEvent(
                    template_code="STORE_LOADOUT_NEXT_VEHICLE",
                    workflow_code="EVENTS",
                    event_type="store_loadout.next_vehicle",
                    entity_type="store_loadout_assignment",
                    entity_id=assignment.id,
                    actor=user.email,
                    channel="in_app",
                    recipient_strategy="static_recipients",
                    resolved_recipients=[lead_email],
                    subject=f"Next vehicle: Store {assignment.store_number} {next_vehicle}",
                    body=(
                        f"Store {assignment.store_number} {label} has departed. "
                        f"Please send {assignment.store_number} {next_vehicle} next."
                    ),
                    status="queued",
                )
            )
    else:
        if (
            assignment.status not in {"signed_complete", "released_from_venue"}
            and assignment.final_review_completed_at is None
        ):
            raise StoreLoadoutError("Vehicle status can be updated after store sign-off")
        statuses = dict(assignment.vehicle_statuses or {})
        position = labels.index(label)
        if position and any(
            statuses.get(name, "expected") != "departed" for name in labels[:position]
        ):
            raise StoreLoadoutError("Vehicles must be handled in the listed truck/van order")
        statuses[label] = payload.status
        assignment.vehicle_statuses = statuses
    db.commit()
    db.refresh(assignment)
    _audit(
        db,
        assignment.event_id,
        assignment.store_loadout_event_id,
        assignment.id,
        None,
        "store_loadout.vehicle.status_updated",
        user.email,
        {"vehicle_label": label, "status": payload.status},
    )
    return _assignment_response(db, assignment, include_items=True)


def latest_store_loadout_signoff(
    db: Session,
    assignment_id: str,
) -> StoreLoadoutSignoffResponse | None:
    signoff = db.scalar(
        select(StoreLoadoutSignoff)
        .where(StoreLoadoutSignoff.assignment_id == assignment_id)
        .order_by(StoreLoadoutSignoff.signed_at.desc())
    )
    return _signoff_response(signoff) if signoff else None


def store_loadout_export_rows(
    db: Session,
    event_id: str,
    report_type: str,
) -> tuple[list[str], list[list[str]]] | None:
    if report_type not in STORE_LOADOUT_EXPORTS:
        raise StoreLoadoutError("Unknown store loadout export type")
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    assignments = db.scalars(
        select(StoreLoadoutAssignment)
        .where(StoreLoadoutAssignment.event_id == event_id)
        .order_by(
            StoreLoadoutAssignment.recommended_departure_at,
            StoreLoadoutAssignment.pickup_priority,
            StoreLoadoutAssignment.store_number,
        )
    ).all()
    store_names = dict(
        db.execute(
            select(Store.store_number, Store.name).where(
                Store.store_number.in_({assignment.store_number for assignment in assignments})
            )
        ).all()
    )
    if report_type == "departure-schedule":
        return (
            [
                "event",
                "store_number",
                "store_name",
                "entity_code",
                "loadout_zone",
                "pickup_priority",
                "distance_miles",
                "estimated_drive_minutes",
                "recommended_departure_at",
                "status",
                "expected_vehicles",
                "vehicle_statuses",
                "team_name",
                "team_member_emails",
                "team_lead_emails",
                "final_review_requested_at",
                "final_review_completed_at",
                "final_review_completed_by",
                "final_review_notes",
            ],
            [
                [
                    event.name,
                    assignment.store_number,
                    store_names.get(assignment.store_number, ""),
                    assignment.entity_code or "",
                    assignment.loadout_zone or "",
                    str(assignment.pickup_priority),
                    str(assignment.distance_miles or ""),
                    str(assignment.estimated_drive_minutes or ""),
                    _dt(assignment.recommended_departure_at),
                    assignment.status,
                    ", ".join(assignment.vehicle_labels or []) or "Truck 1",
                    ", ".join(
                        f"{label}:{(assignment.vehicle_statuses or {}).get(label, 'expected')}"
                        for label in ordered_vehicle_labels(assignment.vehicle_labels)
                    ),
                    assignment.team_name or "",
                    ", ".join(assignment.team_member_emails or []),
                    ", ".join(assignment.team_lead_emails or []),
                    _dt(assignment.final_review_requested_at),
                    _dt(assignment.final_review_completed_at),
                    assignment.final_review_completed_by or "",
                    assignment.final_review_notes or "",
                ]
                for assignment in assignments
            ],
        )
    if report_type == "audit-log":
        logs = db.scalars(
            select(StoreLoadoutAuditLog)
            .where(StoreLoadoutAuditLog.event_id == event_id)
            .order_by(StoreLoadoutAuditLog.created_at)
        ).all()
        return (
            ["event", "created_at", "action", "actor", "assignment_id", "item_id", "payload"],
            [
                [
                    event.name,
                    _dt(log.created_at),
                    log.action,
                    log.actor,
                    log.assignment_id or "",
                    log.loadout_item_id or "",
                    str(log.payload or {}),
                ]
                for log in logs
            ],
        )
    headers = [
        "event",
        "store_number",
        "store_name",
        "assignment_status",
        "loadout_zone",
        "recommended_departure_at",
        "signed_at",
        "released_at",
        "booth_number",
        "vendor_code",
        "item_name",
        "model_number",
        "serial_number",
        "vehicle_label",
        "quantity_assigned",
        "quantity_found",
        "item_status",
        "damage_notes",
        "missing_notes",
        "team_name",
        "team_member_emails",
        "team_lead_emails",
        "final_review_requested_at",
        "final_review_completed_at",
        "final_review_completed_by",
        "final_review_notes",
    ]
    rows: list[list[str]] = []
    items_by_assignment: dict[str, list[StoreLoadoutItem]] = {
        assignment.id: [] for assignment in assignments
    }
    for item in db.scalars(
        select(StoreLoadoutItem)
        .where(StoreLoadoutItem.event_id == event_id)
        .order_by(
            StoreLoadoutItem.assignment_id,
            StoreLoadoutItem.booth_number,
            StoreLoadoutItem.item_name,
        )
    ).all():
        if item.assignment_id in items_by_assignment:
            items_by_assignment[item.assignment_id].append(item)
    for assignment in assignments:
        for item in items_by_assignment[assignment.id]:
            if report_type == "damaged-items" and item.status != "damaged":
                continue
            if report_type == "missing-items" and item.status not in {
                "missing",
                "quantity_mismatch",
            }:
                continue
            rows.append(
                [
                    event.name,
                    assignment.store_number,
                    store_names.get(assignment.store_number, ""),
                    assignment.status,
                    assignment.loadout_zone or "",
                    _dt(assignment.recommended_departure_at),
                    _dt(assignment.signed_at),
                    _dt(assignment.released_at),
                    item.booth_number,
                    item.vendor_code,
                    item.item_name,
                    item.model_number or "",
                    item.serial_number or "",
                    item.vehicle_label or "",
                    str(item.quantity_assigned),
                    str(item.quantity_found),
                    item.status,
                    item.damage_notes or "",
                    item.missing_notes or "",
                    assignment.team_name or "",
                    ", ".join(assignment.team_member_emails or []),
                    ", ".join(assignment.team_lead_emails or []),
                    _dt(assignment.final_review_requested_at),
                    _dt(assignment.final_review_completed_at),
                    assignment.final_review_completed_by or "",
                    assignment.final_review_notes or "",
                ]
            )
    return headers, rows


def store_loadout_packing_lists_pdf(
    db: Session,
    event_id: str,
    assignment_id: str | None = None,
    actor: str | None = None,
) -> bytes | None:
    """Create one printable packing-list manifest section per assigned store."""
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    assignments = list_store_loadout_assignments(db, event_id) or []
    if assignment_id is not None:
        assignments = [assignment for assignment in assignments if assignment.id == assignment_id]
        if not assignments:
            return None
    if actor:
        for assignment in assignments:
            _audit(
                db,
                event_id,
                assignment.store_loadout_event_id,
                assignment.id,
                None,
                "store_loadout.packing_list.reprinted",
                actor,
                {"store_number": assignment.store_number},
            )
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )
    styles = getSampleStyleSheet()
    table_cell_style = ParagraphStyle(
        "LoadoutTableCell",
        parent=styles["BodyText"],
        fontSize=6.8,
        leading=8,
        spaceAfter=0,
        wordWrap="CJK",
    )
    table_header_style = ParagraphStyle(
        "LoadoutTableHeader",
        parent=table_cell_style,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )

    def cell(value: object, header: bool = False) -> Paragraph:
        # Escape report text for XML-safe rendering; no XML input is parsed here.
        return Paragraph(escape(str(value)), table_header_style if header else table_cell_style)

    story = []
    for index, assignment in enumerate(assignments):
        if index:
            story.append(PageBreak())
        vehicle_status_text = ", ".join(
            f"{label} ({(assignment.vehicle_statuses or {}).get(label, 'expected')})"
            for label in ordered_vehicle_labels(assignment.vehicle_labels)
        )
        evidence = db.scalars(
            select(StoreLoadoutItemAttachment)
            .where(StoreLoadoutItemAttachment.assignment_id == assignment.id)
            .order_by(StoreLoadoutItemAttachment.created_at)
        ).all()
        evidence_by_item: dict[str, list[StoreLoadoutItemAttachment]] = {}
        for attachment in evidence:
            evidence_by_item.setdefault(attachment.loadout_item_id, []).append(attachment)
        story.extend(
            [
                Paragraph(f"{event.name} — Store Loadout Packing List", styles["Title"]),
                Paragraph(
                    f"Store {assignment.store_number} · {assignment.store_name or ''}",
                    styles["Heading2"],
                ),
                Paragraph(
                    "<b>Manager:</b> "
                    f"{assignment.store_manager_name or 'Not listed'} · "
                    f"<b>Phone:</b> {assignment.store_phone or 'Not listed'} · "
                    f"<b>Email:</b> {assignment.store_manager_email or 'Not listed'}<br/>"
                    f"<b>Address:</b> {assignment.store_address or 'Not listed'}<br/>"
                    f"<b>Team:</b> {assignment.team_name or 'Unassigned'} · "
                    f"<b>Load order:</b> {assignment.pickup_priority}<br/>"
                    f"<b>Vehicles:</b> {vehicle_status_text}<br/>"
                    f"<b>Route:</b> {assignment.distance_miles or 'TBD'} miles · "
                    f"{assignment.estimated_drive_minutes or 'TBD'} minutes · "
                    f"<b>Recommended departure:</b> {_dt(assignment.recommended_departure_at)}",
                    styles["BodyText"],
                ),
                Spacer(1, 0.18 * inch),
            ]
        )
        rows = [
            [
                cell("Model #", True),
                cell("Description", True),
                cell("Vendor", True),
                cell("Booth", True),
                cell("Qty", True),
                cell("Photos", True),
                cell("Discrepancy notes", True),
            ]
        ]
        for item in assignment.items:
            notes = " · ".join(
                value for value in (item.notes, item.damage_notes, item.missing_notes) if value
            )
            item_evidence = evidence_by_item.get(item.id, [])
            evidence_cell: object = str(len(item_evidence))
            if item_evidence:
                evidence_cell = [
                    Image(BytesIO(item_evidence[0].content), width=0.42 * inch, height=0.42 * inch),
                    Paragraph(f"{len(item_evidence)} photo(s)", styles["BodyText"]),
                ]
            rows.append(
                [
                    cell(item.model_number or "—"),
                    cell(item.item_name or "—"),
                    cell(item.vendor_name or item.vendor_code or "—"),
                    cell(item.booth_number or "TBD"),
                    cell(item.quantity_assigned),
                    evidence_cell,
                    cell(notes or "—"),
                ]
            )
        table = Table(
            rows,
            repeatRows=1,
            colWidths=[
                0.8 * inch,
                1.65 * inch,
                1.1 * inch,
                0.55 * inch,
                0.35 * inch,
                0.45 * inch,
                1.9 * inch,
            ],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b1f44")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#94a3b8")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f1f5f9")],
                    ),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.18 * inch))
        story.append(
            Paragraph(
                "Staff final review: ____________________   Date/time: ____________________",
                styles["BodyText"],
            )
        )
    if not assignments:
        story.append(Paragraph(f"{event.name} — No store loadout assignments", styles["Title"]))
    document.build(story)
    return output.getvalue()


def store_loadout_summary(db: Session, event_id: str) -> StoreLoadoutSummaryResponse | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    loadout = get_store_loadout(db, event_id)
    if loadout is None:
        return StoreLoadoutSummaryResponse(
            event_id=event_id,
            event_name=event.name,
            store_loadout_event_id=None,
            assignment_total=0,
            not_started=0,
            in_progress=0,
            exceptions_present=0,
            ready_for_final_review=0,
            signed_complete=0,
            released_from_venue=0,
            item_total=0,
            items_found=0,
            items_damaged=0,
            items_missing=0,
            completion_percentage=0,
            teams=[],
        )
    assignments = db.scalars(
        select(StoreLoadoutAssignment).where(StoreLoadoutAssignment.event_id == event_id)
    ).all()
    status_counts = {
        status: 0
        for status in (
            "not_started",
            "in_progress",
            "exceptions_present",
            "ready_for_final_review",
            "signed_complete",
            "released_from_venue",
        )
    }
    for assignment in assignments:
        status_counts[assignment.status] = status_counts.get(assignment.status, 0) + 1
    grouped_teams: dict[str, list[StoreLoadoutAssignment]] = {}
    for assignment in assignments:
        grouped_teams.setdefault(assignment.team_name or "Unassigned", []).append(assignment)
    teams: list[StoreLoadoutTeamSummary] = []
    for team_name, team_assignments in sorted(grouped_teams.items()):
        total = len(team_assignments)
        reviewed = sum(item.final_review_completed_at is not None for item in team_assignments)
        signed = sum(
            item.status in {"signed_complete", "released_from_venue"} for item in team_assignments
        )
        released = sum(item.status == "released_from_venue" for item in team_assignments)
        if released == total:
            team_status = "complete"
        elif signed == total and total:
            team_status = "ready_to_load"
        elif reviewed == total and total:
            team_status = "review_complete"
        elif reviewed or signed:
            team_status = "in_progress"
        else:
            team_status = "not_started"
        teams.append(
            StoreLoadoutTeamSummary(
                team_name=team_name,
                status=team_status,
                assignment_total=total,
                reviewed=reviewed,
                signed=signed,
                released=released,
                completion_percentage=round((released / total) * 100, 1) if total else 0,
            )
        )
    return StoreLoadoutSummaryResponse(
        event_id=event_id,
        event_name=event.name,
        store_loadout_event_id=loadout.id,
        assignment_total=len(assignments),
        not_started=status_counts["not_started"],
        in_progress=status_counts["in_progress"],
        exceptions_present=status_counts["exceptions_present"],
        ready_for_final_review=status_counts["ready_for_final_review"],
        signed_complete=status_counts["signed_complete"],
        released_from_venue=status_counts["released_from_venue"],
        item_total=_event_item_count(db, event_id),
        items_found=_event_item_status_count(db, event_id, "found"),
        items_damaged=_event_item_status_count(db, event_id, "damaged"),
        items_missing=_event_item_status_count(db, event_id, "missing"),
        completion_percentage=round(
            (status_counts["released_from_venue"] / len(assignments)) * 100, 1
        )
        if assignments
        else 0,
        teams=teams,
    )


def _event_response(db: Session, loadout: StoreLoadoutEvent) -> StoreLoadoutEventResponse:
    event = db.get(ManagedEvent, loadout.event_id)
    return StoreLoadoutEventResponse(
        id=loadout.id,
        event_id=loadout.event_id,
        event_name=event.name if event else "Event",
        status=loadout.status,
        opens_at=loadout.opens_at,
        loadout_deadline=loadout.loadout_deadline,
        default_loadout_zone=loadout.default_loadout_zone,
        venue_departure_notes=loadout.venue_departure_notes,
        dock_master_email=loadout.dock_master_email,
        created_at=loadout.created_at,
        updated_at=loadout.updated_at,
        completed_at=loadout.completed_at,
    )


def _assignment_response(
    db: Session,
    assignment: StoreLoadoutAssignment,
    include_items: bool,
) -> StoreLoadoutAssignmentResponse:
    return _assignment_responses(db, [assignment], include_items=include_items)[0]


def _assignment_responses(
    db: Session,
    assignments: list[StoreLoadoutAssignment],
    *,
    include_items: bool,
) -> list[StoreLoadoutAssignmentResponse]:
    """Build assignment payloads with fixed-size batched lookups."""
    if not assignments:
        return []

    event_names = dict(
        db.execute(
            select(ManagedEvent.id, ManagedEvent.name).where(
                ManagedEvent.id.in_({assignment.event_id for assignment in assignments})
            )
        ).all()
    )
    store_names = dict(
        db.execute(
            select(Store.store_number, Store.name).where(
                Store.store_number.in_({assignment.store_number for assignment in assignments})
            )
        ).all()
    )
    stores = {
        store.store_number: store
        for store in db.scalars(
            select(Store).where(
                Store.store_number.in_({assignment.store_number for assignment in assignments})
            )
        ).all()
    }
    assignment_ids = {assignment.id for assignment in assignments}
    items = db.scalars(
        select(StoreLoadoutItem)
        .where(StoreLoadoutItem.assignment_id.in_(assignment_ids))
        .order_by(
            StoreLoadoutItem.assignment_id,
            StoreLoadoutItem.booth_number,
            StoreLoadoutItem.item_name,
        )
    ).all()
    items_by_assignment: dict[str, list[StoreLoadoutItem]] = {
        assignment_id: [] for assignment_id in assignment_ids
    }
    for item in items:
        items_by_assignment[item.assignment_id].append(item)
    vendor_names = dict(
        db.execute(
            select(CatalogVendor.vendor_code, CatalogVendor.name).where(
                CatalogVendor.vendor_code.in_({item.vendor_code for item in items})
            )
        ).all()
    )
    return [
        _assignment_response_from_context(
            assignment,
            event_name=event_names.get(assignment.event_id, "Event"),
            store_name=store_names.get(assignment.store_number),
            store_manager_name=(
                stores.get(assignment.store_number).general_manager_name
                if stores.get(assignment.store_number)
                else None
            ),
            store_manager_email=(
                stores.get(assignment.store_number).manager_email
                if stores.get(assignment.store_number)
                else None
            ),
            store_phone=(
                stores.get(assignment.store_number).phone
                if stores.get(assignment.store_number)
                else None
            ),
            store_address=(
                ", ".join(
                    value
                    for value in (
                        stores.get(assignment.store_number).address_line1
                        if stores.get(assignment.store_number)
                        else None,
                        stores.get(assignment.store_number).city
                        if stores.get(assignment.store_number)
                        else None,
                        stores.get(assignment.store_number).state_code
                        if stores.get(assignment.store_number)
                        else None,
                        stores.get(assignment.store_number).postal_code
                        if stores.get(assignment.store_number)
                        else None,
                    )
                    if value
                )
                or None
            ),
            items=items_by_assignment[assignment.id],
            vendor_names=vendor_names,
            include_items=include_items,
        )
        for assignment in assignments
    ]


def _assignment_response_from_context(
    assignment: StoreLoadoutAssignment,
    *,
    event_name: str,
    store_name: str | None,
    store_manager_name: str | None,
    store_manager_email: str | None,
    store_phone: str | None,
    store_address: str | None,
    items: list[StoreLoadoutItem],
    vendor_names: dict[str, str],
    include_items: bool,
) -> StoreLoadoutAssignmentResponse:
    return StoreLoadoutAssignmentResponse(
        id=assignment.id,
        store_loadout_event_id=assignment.store_loadout_event_id,
        event_id=assignment.event_id,
        event_name=event_name,
        store_number=assignment.store_number,
        store_name=store_name,
        store_manager_name=store_manager_name,
        store_manager_email=store_manager_email,
        store_phone=store_phone,
        store_address=store_address,
        entity_code=assignment.entity_code,
        status=assignment.status,
        pickup_priority=assignment.pickup_priority,
        loadout_zone=assignment.loadout_zone,
        distance_miles=assignment.distance_miles,
        estimated_drive_minutes=assignment.estimated_drive_minutes,
        recommended_departure_at=assignment.recommended_departure_at,
        notes=assignment.notes,
        team_name=assignment.team_name,
        team_member_emails=assignment.team_member_emails or [],
        team_lead_emails=assignment.team_lead_emails or [],
        vehicle_labels=ordered_vehicle_labels(assignment.vehicle_labels),
        vehicle_statuses=assignment.vehicle_statuses
        or {label: "expected" for label in ordered_vehicle_labels(assignment.vehicle_labels)},
        final_review_requested_at=assignment.final_review_requested_at,
        final_review_requested_by=assignment.final_review_requested_by,
        final_review_completed_at=assignment.final_review_completed_at,
        final_review_completed_by=assignment.final_review_completed_by,
        final_review_notes=assignment.final_review_notes,
        item_count=len(items),
        exception_count=sum(1 for item in items if item.status in EXCEPTION_ITEM_STATUSES),
        signed_at=assignment.signed_at,
        signed_by=assignment.signed_by,
        released_at=assignment.released_at,
        released_by=assignment.released_by,
        updated_at=assignment.updated_at,
        items=[
            _item_response_from_context(item, vendor_names.get(item.vendor_code)) for item in items
        ]
        if include_items
        else [],
    )


def _item_response(db: Session, item: StoreLoadoutItem) -> StoreLoadoutItemResponse:
    vendor = db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == item.vendor_code))
    return _item_response_from_context(item, vendor.name if vendor else None)


def _item_response_from_context(
    item: StoreLoadoutItem,
    vendor_name: str | None,
) -> StoreLoadoutItemResponse:
    return StoreLoadoutItemResponse(
        id=item.id,
        assignment_id=item.assignment_id,
        event_id=item.event_id,
        vendor_hall_booth_id=item.vendor_hall_booth_id,
        vendor_hall_inventory_item_id=item.vendor_hall_inventory_item_id,
        vendor_code=item.vendor_code,
        vendor_name=vendor_name,
        booth_number=item.booth_number,
        item_name=item.item_name,
        model_number=item.model_number,
        serial_number=item.serial_number,
        quantity_assigned=item.quantity_assigned,
        quantity_found=item.quantity_found,
        condition=item.condition,
        status=item.status,
        notes=item.notes,
        damage_notes=item.damage_notes,
        missing_notes=item.missing_notes,
        vehicle_label=item.vehicle_label,
        updated_at=item.updated_at,
    )


def _checkin_response(checkin: StoreLoadoutItemCheckin) -> StoreLoadoutItemCheckinResponse:
    return StoreLoadoutItemCheckinResponse(
        id=checkin.id,
        loadout_item_id=checkin.loadout_item_id,
        assignment_id=checkin.assignment_id,
        status=checkin.status,
        quantity_found=checkin.quantity_found,
        damage_notes=checkin.damage_notes,
        missing_notes=checkin.missing_notes,
        checked_by=checkin.checked_by,
        checked_at=checkin.checked_at,
    )


def _signoff_response(signoff: StoreLoadoutSignoff) -> StoreLoadoutSignoffResponse:
    return StoreLoadoutSignoffResponse(
        id=signoff.id,
        assignment_id=signoff.assignment_id,
        signer_name=signoff.signer_name,
        signer_email=signoff.signer_email,
        signature_text=signoff.signature_text,
        exception_summary=signoff.exception_summary,
        signed_at=signoff.signed_at,
    )


def _assignment_items(db: Session, assignment_id: str) -> list[StoreLoadoutItem]:
    return list(
        db.scalars(
            select(StoreLoadoutItem)
            .where(StoreLoadoutItem.assignment_id == assignment_id)
            .order_by(StoreLoadoutItem.booth_number, StoreLoadoutItem.item_name)
        ).all()
    )


def _derive_item_status(item_quantity_assigned: int, payload: StoreLoadoutItemCheckinWrite) -> str:
    if payload.status == "found" and payload.quantity_found != item_quantity_assigned:
        return "quantity_mismatch"
    return payload.status


def _refresh_assignment_status(db: Session, assignment: StoreLoadoutAssignment) -> None:
    if assignment.status in {"signed_complete", "released_from_venue"}:
        return
    items = _assignment_items(db, assignment.id)
    if not items or all(item.status == "assigned" for item in items):
        assignment.status = "not_started"
        return
    if any(item.status in EXCEPTION_ITEM_STATUSES for item in items):
        assignment.status = "exceptions_present"
        return
    if all(item.status in ACCOUNTED_ITEM_STATUSES for item in items):
        assignment.status = "ready_for_final_review"
        return
    assignment.status = "in_progress"


def _assignment_visible_to_user(
    db: Session,
    assignment: StoreLoadoutAssignment,
    user: User,
) -> bool:
    if _has_loadout_manager_access(db, user, assignment.event_id):
        return True
    if user.email in (assignment.team_member_emails or []):
        return True
    if user.email in (assignment.team_lead_emails or []):
        return True
    if user.home_store_number and user.home_store_number == assignment.store_number:
        return True
    if assignment.entity_code is None:
        return False
    membership_exists = db.scalar(
        select(EventMembership.id).where(
            EventMembership.event_id == assignment.event_id,
            EventMembership.user_id == user.id,
            EventMembership.membership_type == "franchise_representative",
            EventMembership.entity_code == assignment.entity_code,
            EventMembership.is_active.is_(True),
        )
    )
    return membership_exists is not None


def _dock_phase_assignments(
    assignments: list[StoreLoadoutAssignment],
    user: User,
) -> list[StoreLoadoutAssignment]:
    """During dock loading, team leads see only their active and next team."""
    led = [
        assignment
        for assignment in assignments
        if user.email in (assignment.team_lead_emails or [])
    ]
    if not led:
        return assignments
    teams: dict[str, list[StoreLoadoutAssignment]] = {}
    for assignment in led:
        teams.setdefault(assignment.team_name or "Unassigned", []).append(assignment)
    ordered = sorted(teams.items(), key=lambda pair: min(item.pickup_priority for item in pair[1]))
    active_index = 0
    for index, (_, team_assignments) in enumerate(ordered):
        if all(item.status == "released_from_venue" for item in team_assignments):
            active_index = min(index + 1, len(ordered) - 1)
            continue
        if any(
            item.status in {"signed_complete", "released_from_venue"} for item in team_assignments
        ):
            active_index = index
            break
        if all(item.final_review_completed_at is not None for item in team_assignments):
            active_index = index
            break
    allowed = {name for name, _ in ordered[active_index : active_index + 2]}
    return [assignment for assignment in led if (assignment.team_name or "Unassigned") in allowed]


def _user_has_permission(user: User, permission_code: str) -> bool:
    return any(
        permission.code == permission_code for role in user.roles for permission in role.permissions
    )


def _has_loadout_manager_access(db: Session, user: User, event_id: str) -> bool:
    if _user_has_permission(user, "store_loadout.manage"):
        return True
    return (
        db.scalar(
            select(EventMembership.id).where(
                EventMembership.event_id == event_id,
                EventMembership.user_id == user.id,
                (
                    EventMembership.loadout_role.in_(("dockmaster", "overseer"))
                    | EventMembership.membership_type.in_(("dockmaster", "overseer"))
                ),
                EventMembership.is_active.is_(True),
            )
        )
        is not None
    )


def _dt(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _assigned_quantity(db: Session, inventory_item_id: str) -> int:
    return (
        db.scalar(
            select(func.sum(StoreLoadoutItem.quantity_assigned)).where(
                StoreLoadoutItem.vendor_hall_inventory_item_id == inventory_item_id
            )
        )
        or 0
    )


def _event_item_count(db: Session, event_id: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(StoreLoadoutItem)
            .where(StoreLoadoutItem.event_id == event_id)
        )
        or 0
    )


def _event_item_status_count(db: Session, event_id: str, status: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(StoreLoadoutItem)
            .where(StoreLoadoutItem.event_id == event_id, StoreLoadoutItem.status == status)
        )
        or 0
    )


def _audit(
    db: Session,
    event_id: str,
    loadout_id: str,
    assignment_id: str | None,
    item_id: str | None,
    action: str,
    actor: str,
    payload: dict,
) -> None:
    db.add(
        StoreLoadoutAuditLog(
            event_id=event_id,
            store_loadout_event_id=loadout_id,
            assignment_id=assignment_id,
            loadout_item_id=item_id,
            action=action,
            actor=actor,
            payload=payload,
        )
    )
    db.commit()
