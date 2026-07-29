from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import CatalogProduct
from app.models.event_management import (
    EventEntityOrder,
    EventFeedbackResponse,
    EventMembership,
    EventPoll,
    EventPresentationState,
    EventProductSlide,
    EventSettlementAuditLog,
    EventSettlementEvent,
    EventSettlementException,
    ManagedEvent,
    ManagedSubEvent,
    StoreLoadoutAssignment,
    StoreLoadoutItem,
    VendorHallBooth,
    VendorHallEvent,
)
from app.models.purchasing import PurchaseRequest
from app.models.store import Store
from app.schemas.event_settlement import (
    EventSettlementExceptionResolutionWrite,
    EventSettlementExceptionResponse,
    EventSettlementExceptionWrite,
    EventSettlementSummaryResponse,
    EventSettlementWrite,
)
from app.services.event_access_service import event_operations_are_locked
from app.services.event_order_backup_service import archive_event_order_backup
from app.services.event_product_slide_service import purge_event_slide_images


class EventSettlementError(ValueError):
    pass


EVENT_SETTLEMENT_EXPORTS = {
    "summary",
    "closeout-packet",
    "reconciliation-detail",
    "exceptions",
    "order-closeout",
    "loadout-closeout",
    "audit-log",
    "feedback",
}


def configure_event_settlement(
    db: Session,
    event_id: str,
    payload: EventSettlementWrite,
    actor: str,
) -> EventSettlementSummaryResponse | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    settlement = get_event_settlement(db, event_id)
    if settlement is not None and settlement.status == "closed" and payload.status != "closed":
        raise EventSettlementError("Closed event settlements cannot be reopened or changed")
    if event_operations_are_locked(db, event_id):
        raise EventSettlementError("Archived event settlements are read-only")
    if settlement is None:
        settlement = EventSettlementEvent(event_id=event_id, created_by=actor)
        db.add(settlement)
        db.flush()
    if payload.status in {"approved", "closed"}:
        _validate_settlement_ready_for_close(db, event_id)
    decision_at = datetime.now(UTC)
    backup_artifact = None
    settlement.status = payload.status
    settlement.notes = payload.notes
    if payload.status == "approved" and settlement.approved_at is None:
        settlement.approved_at = decision_at
        settlement.approved_by = actor
    if payload.status == "closed":
        if settlement.approved_at is None:
            settlement.approved_at = decision_at
            settlement.approved_by = actor
        if settlement.closed_at is None:
            settlement.closed_at = decision_at
            settlement.closed_by = actor
        event.status = "completed"
        for sub_event in db.scalars(
            select(ManagedSubEvent).where(ManagedSubEvent.event_id == event_id)
        ).all():
            if sub_event.status != "cancelled":
                sub_event.status = "completed"
        for presentation in db.scalars(
            select(EventPresentationState).where(EventPresentationState.event_id == event_id)
        ).all():
            presentation.status = "ended"
            presentation.ordering_status = "closed"
            presentation.updated_by = actor
        for poll in db.scalars(select(EventPoll).where(EventPoll.event_id == event_id)).all():
            if poll.status != "closed":
                poll.status = "closed"
                poll.closed_at = decision_at
        backup_artifact = archive_event_order_backup(db, event_id, actor)
        purge_event_slide_images(db, event_id)
    db.add(
        EventSettlementAuditLog(
            event_id=event_id,
            settlement_event_id=settlement.id,
            action=(
                "event_settlement.closed"
                if payload.status == "closed"
                else "event_settlement.approved"
                if payload.status == "approved"
                else "event_settlement.configured"
            ),
            actor=actor,
            payload={
                **payload.model_dump(),
                "approved_at": settlement.approved_at.isoformat()
                if settlement.approved_at
                else None,
                "approved_by": settlement.approved_by,
                "closed_at": settlement.closed_at.isoformat() if settlement.closed_at else None,
                "closed_by": settlement.closed_by,
                "order_backup_artifact_id": backup_artifact.id if backup_artifact else None,
                "order_backup_sha256": backup_artifact.sha256 if backup_artifact else None,
            },
        )
    )
    db.commit()
    return event_settlement_summary(db, event_id)


def create_event_settlement_exception(
    db: Session,
    event_id: str,
    payload: EventSettlementExceptionWrite,
    actor: str,
) -> EventSettlementSummaryResponse | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    settlement = _ensure_settlement(db, event_id, actor)
    _require_open_settlement(settlement)
    if event_operations_are_locked(db, event_id):
        raise EventSettlementError("Archived event settlements are read-only")
    exception = EventSettlementException(
        settlement_event_id=settlement.id,
        event_id=event_id,
        exception_type=payload.exception_type,
        severity=payload.severity,
        status="open",
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        description=payload.description,
        created_by=actor,
    )
    db.add(exception)
    db.flush()
    _audit(
        db,
        event_id,
        settlement.id,
        "event_settlement.exception.created",
        actor,
        {
            "exception_id": exception.id,
            **payload.model_dump(),
        },
    )
    db.commit()
    return event_settlement_summary(db, event_id)


def resolve_event_settlement_exception(
    db: Session,
    exception_id: str,
    payload: EventSettlementExceptionResolutionWrite,
    actor: str,
) -> EventSettlementSummaryResponse | None:
    exception = db.get(EventSettlementException, exception_id)
    if exception is None:
        return None
    _require_open_settlement(exception.settlement_event)
    if event_operations_are_locked(db, exception.event_id):
        raise EventSettlementError("Archived event settlements are read-only")
    exception.status = "resolved"
    exception.resolved_by = actor
    exception.resolved_at = datetime.now(UTC)
    exception.resolution_notes = payload.resolution_notes
    _audit(
        db,
        exception.event_id,
        exception.settlement_event_id,
        "event_settlement.exception.resolved",
        actor,
        {
            "exception_id": exception.id,
            "resolution_notes": payload.resolution_notes,
        },
    )
    db.commit()
    return event_settlement_summary(db, exception.event_id)


def reopen_event_settlement_exception(
    db: Session,
    exception_id: str,
    actor: str,
) -> EventSettlementSummaryResponse | None:
    exception = db.get(EventSettlementException, exception_id)
    if exception is None:
        return None
    _require_open_settlement(exception.settlement_event)
    if event_operations_are_locked(db, exception.event_id):
        raise EventSettlementError("Archived event settlements are read-only")
    exception.status = "open"
    exception.resolved_by = None
    exception.resolved_at = None
    exception.resolution_notes = None
    _audit(
        db,
        exception.event_id,
        exception.settlement_event_id,
        "event_settlement.exception.reopened",
        actor,
        {"exception_id": exception.id},
    )
    db.commit()
    return event_settlement_summary(db, exception.event_id)


def get_event_settlement(db: Session, event_id: str) -> EventSettlementEvent | None:
    return db.scalar(select(EventSettlementEvent).where(EventSettlementEvent.event_id == event_id))


def _ensure_settlement(db: Session, event_id: str, actor: str) -> EventSettlementEvent:
    settlement = get_event_settlement(db, event_id)
    if settlement is None:
        settlement = EventSettlementEvent(event_id=event_id, created_by=actor)
        db.add(settlement)
        db.flush()
    return settlement


def _require_open_settlement(settlement: EventSettlementEvent) -> None:
    if settlement.status == "closed":
        raise EventSettlementError("Closed event settlements cannot be changed")


def event_settlement_summary(
    db: Session,
    event_id: str,
) -> EventSettlementSummaryResponse | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    settlement = get_event_settlement(db, event_id)
    generated = _generated_exceptions(db, settlement, event_id)
    stored = _stored_exceptions(db, settlement.id) if settlement else []
    all_exceptions = [*generated, *stored]
    open_exceptions = [item for item in all_exceptions if item.status == "open"]
    open_type_counts = _open_exception_type_counts(open_exceptions)
    order_total = _order_count(db, event_id)
    order_released = _order_count(db, event_id, "released")
    approved_units = _approved_units(db, event_id)
    approved_spend = _approved_spend(db, event_id)
    loadout_total = _loadout_count(db, event_id)
    loadout_signed = _loadout_status_count(db, event_id, {"signed_complete", "released_from_venue"})
    loadout_released = _loadout_status_count(db, event_id, {"released_from_venue"})
    loadout_final_review_pending = _loadout_final_review_pending_count(db, event_id)
    required = order_total + loadout_total
    complete = order_released + loadout_released
    readiness = Decimal("100.00") if required == 0 else Decimal(complete * 100) / Decimal(required)
    status = settlement.status if settlement else "draft"
    hall = db.scalar(select(VendorHallEvent).where(VendorHallEvent.event_id == event_id))
    hall_booth_count = (
        db.scalar(
            select(func.count())
            .select_from(VendorHallBooth)
            .where(VendorHallBooth.vendor_hall_event_id == hall.id)
        )
        if hall is not None
        else 0
    ) or 0
    vendor_hall_closeout_ready = (
        None if hall is None or hall_booth_count == 0 else hall.status == "closed"
    )
    if open_exceptions:
        status = "exceptions_present"
    elif required and complete >= required and status not in {"approved", "closed"}:
        status = "ready_for_review"
    return EventSettlementSummaryResponse(
        event_id=event.id,
        event_name=event.name,
        settlement_event_id=settlement.id if settlement else None,
        status=status,
        vendor_hall_status=hall.status if hall is not None else None,
        vendor_hall_closeout_ready=vendor_hall_closeout_ready,
        order_total=order_total,
        order_released=order_released,
        approved_units=approved_units,
        approved_spend=approved_spend,
        loadout_assignment_total=loadout_total,
        loadout_signed=loadout_signed,
        loadout_released=loadout_released,
        loadout_exception_assignments=_loadout_exception_count(db, event_id),
        loadout_final_review_pending=loadout_final_review_pending,
        ordered_not_loaded_count=open_type_counts["ordered_not_loaded"],
        loaded_not_ordered_count=open_type_counts["loaded_not_ordered"],
        quantity_mismatch_count=open_type_counts["quantity_mismatch"],
        open_exception_count=len(open_exceptions),
        readiness_percentage=readiness.quantize(Decimal("0.01")),
        exceptions=all_exceptions,
        notes=settlement.notes if settlement else None,
        approved_at=settlement.approved_at if settlement else None,
        approved_by=settlement.approved_by if settlement else None,
        closed_at=settlement.closed_at if settlement else None,
        closed_by=settlement.closed_by if settlement else None,
        updated_at=settlement.updated_at if settlement else None,
    )


def _generated_exceptions(
    db: Session,
    settlement: EventSettlementEvent | None,
    event_id: str,
) -> list[EventSettlementExceptionResponse]:
    settlement_id = settlement.id if settlement else "generated"
    generated: list[EventSettlementExceptionResponse] = []
    for assignment in db.scalars(
        select(StoreLoadoutAssignment).where(StoreLoadoutAssignment.event_id == event_id)
    ):
        if assignment.status in {"exceptions_present"}:
            generated.append(
                _generated_exception(
                    settlement_id,
                    "loadout_exception",
                    "high",
                    "assignment",
                    assignment.id,
                    f"Store {assignment.store_number} has unresolved loadout exceptions.",
                )
            )
        if (
            assignment.status == "ready_for_final_review"
            and assignment.final_review_completed_at is None
        ):
            lead_detail = ""
            if assignment.team_lead_emails:
                lead_detail = f" Event staff lead: {', '.join(assignment.team_lead_emails)}."
            generated.append(
                _generated_exception(
                    settlement_id,
                    "loadout_final_review_pending",
                    "medium",
                    "assignment",
                    assignment.id,
                    (
                        f"Store {assignment.store_number} loadout is ready for event staff "
                        f"final review.{lead_detail}"
                    ),
                )
            )
        if assignment.status not in {"signed_complete", "released_from_venue"}:
            generated.append(
                _generated_exception(
                    settlement_id,
                    "unsigned_packing_list",
                    "medium",
                    "assignment",
                    assignment.id,
                    f"Store {assignment.store_number} has not signed its final packing list.",
                )
            )
        elif assignment.status != "released_from_venue":
            generated.append(
                _generated_exception(
                    settlement_id,
                    "unreleased_store",
                    "medium",
                    "assignment",
                    assignment.id,
                    f"Store {assignment.store_number} is signed but not released from the venue.",
                )
            )
    unreleased_orders = db.scalars(
        select(EventEntityOrder).where(
            EventEntityOrder.event_id == event_id,
            EventEntityOrder.review_status.in_(["pending", "approved"]),
        )
    ).all()
    for order in unreleased_orders:
        generated.append(
            _generated_exception(
                settlement_id,
                "unreleased_order",
                "medium",
                "order",
                order.id,
                f"Entity {order.entity_code} order is not released for settlement.",
            )
        )
    for request in _event_buy_fair_requests(db, event_id):
        if request.status == "vendor_draft":
            generated.append(
                _generated_exception(
                    settlement_id,
                    "unsubmitted_buy_fair_order",
                    "medium",
                    "purchase_request",
                    request.id,
                    f"Vendor buy fair order {request.order_number} has not been submitted.",
                )
            )
    generated.extend(_order_loadout_match_exceptions(db, settlement_id, event_id))
    return generated


def _open_exception_type_counts(
    exceptions: list[EventSettlementExceptionResponse],
) -> dict[str, int]:
    counts: dict[str, int] = {
        "ordered_not_loaded": 0,
        "loaded_not_ordered": 0,
        "quantity_mismatch": 0,
    }
    for exception in exceptions:
        if exception.exception_type in counts:
            counts[exception.exception_type] += 1
    return counts


def _order_loadout_match_exceptions(
    db: Session,
    settlement_id: str,
    event_id: str,
) -> list[EventSettlementExceptionResponse]:
    generated: list[EventSettlementExceptionResponse] = []
    for (
        entity_code,
        vendor_code,
        model_number,
        ordered,
        loaded,
        exception_type,
    ) in _order_loadout_match_rows(db, event_id):
        if not exception_type:
            continue
        reference_id = f"{entity_code}:{vendor_code}:{model_number}"
        if exception_type == "ordered_not_loaded":
            generated.append(
                _generated_exception(
                    settlement_id,
                    "ordered_not_loaded",
                    "high",
                    "order_loadout_match",
                    reference_id,
                    (
                        f"{entity_code} ordered {ordered} unit(s) of {vendor_code} "
                        f"{model_number}, but none are signed in loadout."
                    ),
                )
            )
        elif exception_type == "loaded_not_ordered":
            generated.append(
                _generated_exception(
                    settlement_id,
                    "loaded_not_ordered",
                    "high",
                    "order_loadout_match",
                    reference_id,
                    (
                        f"{entity_code} has {loaded} signed loadout unit(s) of {vendor_code} "
                        f"{model_number}, but no released order exists."
                    ),
                )
            )
        elif exception_type == "quantity_mismatch":
            generated.append(
                _generated_exception(
                    settlement_id,
                    "quantity_mismatch",
                    "high",
                    "order_loadout_match",
                    reference_id,
                    (
                        f"{entity_code} released order quantity for {vendor_code} {model_number} "
                        f"is {ordered}, but signed loadout quantity is {loaded}."
                    ),
                )
            )
    return generated


def _order_loadout_match_rows(
    db: Session,
    event_id: str,
) -> list[tuple[str, str, str, int, int, str]]:
    order_quantities: dict[tuple[str, str, str], int] = defaultdict(int)
    loadout_quantities: dict[tuple[str, str, str], int] = defaultdict(int)
    for order, slide in db.execute(
        select(EventEntityOrder, EventProductSlide)
        .join(EventProductSlide, EventProductSlide.id == EventEntityOrder.slide_id)
        .where(
            EventEntityOrder.event_id == event_id,
            EventEntityOrder.review_status == "released",
        )
    ):
        variants = {str(item["model_number"]): item for item in (slide.product_variants or [])}
        if variants and order.variant_quantities:
            for model_number, quantity in order.variant_quantities.items():
                if quantity > 0 and model_number in variants:
                    order_quantities[(order.entity_code, slide.vendor_code, model_number)] += (
                        quantity
                    )
        else:
            order_quantities[(order.entity_code, slide.vendor_code, slide.model_number)] += (
                order.quantity
            )
    for assignment, item in db.execute(
        select(StoreLoadoutAssignment, StoreLoadoutItem)
        .join(StoreLoadoutItem, StoreLoadoutItem.assignment_id == StoreLoadoutAssignment.id)
        .where(
            StoreLoadoutAssignment.event_id == event_id,
            StoreLoadoutAssignment.status == "released_from_venue",
        )
    ):
        model_number = item.model_number or ""
        if not model_number:
            continue
        loadout_quantities[
            (assignment.entity_code or assignment.store_number, item.vendor_code, model_number)
        ] += item.quantity_assigned
    rows: list[tuple[str, str, str, int, int, str]] = []
    for entity_code, vendor_code, model_number in sorted(
        set(order_quantities) | set(loadout_quantities)
    ):
        key = (entity_code, vendor_code, model_number)
        ordered = order_quantities.get(key, 0)
        loaded = loadout_quantities.get(key, 0)
        exception_type = ""
        if ordered and not loaded:
            exception_type = "ordered_not_loaded"
        elif loaded and not ordered:
            exception_type = "loaded_not_ordered"
        elif ordered != loaded:
            exception_type = "quantity_mismatch"
        rows.append((entity_code, vendor_code, model_number, ordered, loaded, exception_type))
    return rows


def _generated_exception(
    settlement_id: str,
    exception_type: str,
    severity: str,
    reference_type: str,
    reference_id: str,
    description: str,
) -> EventSettlementExceptionResponse:
    return EventSettlementExceptionResponse(
        id=f"generated:{exception_type}:{reference_id}",
        exception_type=exception_type,
        severity=severity,
        status="open",
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        created_at=datetime.now(UTC),
    )


def _stored_exceptions(
    db: Session, settlement_event_id: str
) -> list[EventSettlementExceptionResponse]:
    exceptions = db.scalars(
        select(EventSettlementException).where(
            EventSettlementException.settlement_event_id == settlement_event_id
        )
    ).all()
    return [
        EventSettlementExceptionResponse(
            id=item.id,
            exception_type=item.exception_type,
            severity=item.severity,
            status=item.status,
            reference_type=item.reference_type,
            reference_id=item.reference_id,
            description=item.description,
            created_at=item.created_at,
            resolved_by=item.resolved_by,
            resolved_at=item.resolved_at,
            resolution_notes=item.resolution_notes,
        )
        for item in exceptions
    ]


def _audit(
    db: Session,
    event_id: str,
    settlement_event_id: str,
    action: str,
    actor: str,
    payload: dict,
) -> None:
    db.add(
        EventSettlementAuditLog(
            event_id=event_id,
            settlement_event_id=settlement_event_id,
            action=action,
            actor=actor,
            payload=payload,
        )
    )


def _event_buy_fair_requests(db: Session, event_id: str) -> list[PurchaseRequest]:
    return [
        request
        for request in db.scalars(
            select(PurchaseRequest).where(PurchaseRequest.workflow_code == "VENDOR_ORDER")
        ).all()
        if request.context.get("event_id") == event_id
        and request.context.get("source") == "event_vendor_buy_fair"
        and request.status != "cancelled_by_vendor"
    ]


def _submitted_buy_fair_requests(db: Session, event_id: str) -> list[PurchaseRequest]:
    return [
        request
        for request in _event_buy_fair_requests(db, event_id)
        if request.status != "vendor_draft"
    ]


def _order_count(db: Session, event_id: str, review_status: str | None = None) -> int:
    statement = (
        select(func.count())
        .select_from(EventEntityOrder)
        .where(EventEntityOrder.event_id == event_id)
    )
    if review_status:
        statement = statement.where(EventEntityOrder.review_status == review_status)
    live_count = db.scalar(statement) or 0
    if review_status == "released":
        return live_count + len(_submitted_buy_fair_requests(db, event_id))
    if review_status is None:
        return live_count + len(_event_buy_fair_requests(db, event_id))
    return live_count


def _approved_units(db: Session, event_id: str) -> int:
    live_units = (
        db.scalar(
            select(func.coalesce(func.sum(EventEntityOrder.quantity), 0)).where(
                EventEntityOrder.event_id == event_id,
                EventEntityOrder.review_status.in_(["approved", "released"]),
            )
        )
        or 0
    )
    buy_fair_units = sum(
        (
            line.quantity
            for request in _submitted_buy_fair_requests(db, event_id)
            for line in request.line_items
        ),
        Decimal("0"),
    )
    return int(live_units + buy_fair_units)


def _approved_spend(db: Session, event_id: str) -> Decimal:
    live_spend = db.scalar(
        select(func.coalesce(func.sum(EventEntityOrder.total_cost), 0)).where(
            EventEntityOrder.event_id == event_id,
            EventEntityOrder.review_status.in_(["approved", "released"]),
        )
    ) or Decimal("0")
    return live_spend + sum(
        (request.total for request in _submitted_buy_fair_requests(db, event_id)),
        Decimal("0"),
    )


def _loadout_count(db: Session, event_id: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(StoreLoadoutAssignment)
            .where(StoreLoadoutAssignment.event_id == event_id)
        )
        or 0
    )


def _loadout_status_count(db: Session, event_id: str, statuses: set[str]) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(StoreLoadoutAssignment)
            .where(
                StoreLoadoutAssignment.event_id == event_id,
                StoreLoadoutAssignment.status.in_(statuses),
            )
        )
        or 0
    )


def _loadout_exception_count(db: Session, event_id: str) -> int:
    return _loadout_status_count(db, event_id, {"exceptions_present"})


def _loadout_final_review_pending_count(db: Session, event_id: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(StoreLoadoutAssignment)
            .where(
                StoreLoadoutAssignment.event_id == event_id,
                StoreLoadoutAssignment.status == "ready_for_final_review",
                StoreLoadoutAssignment.final_review_completed_at.is_(None),
            )
        )
        or 0
    )


def _validate_settlement_ready_for_close(db: Session, event_id: str) -> None:
    summary = event_settlement_summary(db, event_id)
    if summary is None:
        raise EventSettlementError("Event not found")
    if summary.open_exception_count:
        raise EventSettlementError(
            "Settlement cannot be approved or closed while open exceptions exist"
        )
    if summary.readiness_percentage < Decimal("100.00"):
        raise EventSettlementError(
            "Settlement cannot be approved or closed until all orders and loadouts are released"
        )
    # Vendor Hall is an operational prerequisite for final event closeout.  Only
    # enforce this when the event has an actual booth program; events that do not
    # use Vendor Hall (or have an empty draft hall) remain eligible for settlement.
    hall = db.scalar(select(VendorHallEvent).where(VendorHallEvent.event_id == event_id))
    if hall is not None:
        booth_count = (
            db.scalar(
                select(func.count())
                .select_from(VendorHallBooth)
                .where(VendorHallBooth.vendor_hall_event_id == hall.id)
            )
            or 0
        )
        if booth_count and hall.status != "closed":
            raise EventSettlementError(
                "Settlement cannot be approved or closed until the Vendor Hall is closed"
            )


def event_settlement_export_rows(
    db: Session,
    event_id: str,
    report_type: str,
) -> tuple[list[str], list[list[str]]] | None:
    if report_type not in EVENT_SETTLEMENT_EXPORTS:
        raise EventSettlementError("Unknown event settlement export type")
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    summary = event_settlement_summary(db, event_id)
    if summary is None:
        return None
    if report_type == "summary":
        return _summary_export_rows(summary)
    if report_type == "closeout-packet":
        return _closeout_packet_export_rows(db, event, summary)
    if report_type == "reconciliation-detail":
        return _reconciliation_detail_export_rows(db, event)
    if report_type == "exceptions":
        return _exception_export_rows(event.name, summary)
    if report_type == "order-closeout":
        return _order_closeout_export_rows(db, event)
    if report_type == "loadout-closeout":
        return _loadout_closeout_export_rows(db, event)
    if report_type == "feedback":
        return _feedback_export_rows(db, event)
    return _audit_export_rows(db, event)


def _summary_export_rows(
    summary: EventSettlementSummaryResponse,
) -> tuple[list[str], list[list[str]]]:
    return (
        ["metric", "value"],
        [
            ["event_id", summary.event_id],
            ["event_name", summary.event_name],
            ["settlement_event_id", summary.settlement_event_id or ""],
            ["status", summary.status],
            ["order_total", str(summary.order_total)],
            ["order_released", str(summary.order_released)],
            ["approved_units", str(summary.approved_units)],
            ["approved_spend", str(summary.approved_spend)],
            ["loadout_assignment_total", str(summary.loadout_assignment_total)],
            ["loadout_signed", str(summary.loadout_signed)],
            ["loadout_released", str(summary.loadout_released)],
            [
                "loadout_exception_assignments",
                str(summary.loadout_exception_assignments),
            ],
            [
                "loadout_final_review_pending",
                str(summary.loadout_final_review_pending),
            ],
            ["ordered_not_loaded_count", str(summary.ordered_not_loaded_count)],
            ["loaded_not_ordered_count", str(summary.loaded_not_ordered_count)],
            ["quantity_mismatch_count", str(summary.quantity_mismatch_count)],
            ["open_exception_count", str(summary.open_exception_count)],
            ["readiness_percentage", str(summary.readiness_percentage)],
            ["notes", summary.notes or ""],
            ["approved_at", _dt(summary.approved_at)],
            ["approved_by", summary.approved_by or ""],
            ["closed_at", _dt(summary.closed_at)],
            ["closed_by", summary.closed_by or ""],
            ["updated_at", _dt(summary.updated_at)],
        ],
    )


def _closeout_packet_export_rows(
    db: Session,
    event: ManagedEvent,
    summary: EventSettlementSummaryResponse,
) -> tuple[list[str], list[list[str]]]:
    rows: list[list[str]] = []
    _append_packet_rows(rows, "summary", _summary_export_rows(summary))
    _append_packet_rows(rows, "exceptions", _exception_export_rows(event.name, summary))
    _append_packet_rows(
        rows, "reconciliation_detail", _reconciliation_detail_export_rows(db, event)
    )
    _append_packet_rows(rows, "order_closeout", _order_closeout_export_rows(db, event))
    _append_packet_rows(rows, "loadout_closeout", _loadout_closeout_export_rows(db, event))
    _append_packet_rows(rows, "feedback", _feedback_export_rows(db, event))
    _append_packet_rows(rows, "audit_log", _audit_export_rows(db, event))
    return ["section", "row_number", "field", "value"], rows


def _append_packet_rows(
    packet_rows: list[list[str]],
    section: str,
    export: tuple[list[str], list[list[str]]],
) -> None:
    headers, rows = export
    if not rows:
        packet_rows.append([section, "0", "empty", ""])
        return
    for row_number, row in enumerate(rows, start=1):
        for index, header in enumerate(headers):
            packet_rows.append(
                [
                    section,
                    str(row_number),
                    header,
                    row[index] if index < len(row) else "",
                ]
            )


def _reconciliation_detail_export_rows(
    db: Session,
    event: ManagedEvent,
) -> tuple[list[str], list[list[str]]]:
    return (
        [
            "event",
            "entity_code",
            "vendor_code",
            "model_number",
            "released_order_quantity",
            "released_loadout_quantity",
            "variance",
            "exception_type",
        ],
        [
            [
                event.name,
                entity_code,
                vendor_code,
                model_number,
                str(ordered),
                str(loaded),
                str(loaded - ordered),
                exception_type,
            ]
            for entity_code, vendor_code, model_number, ordered, loaded, exception_type in (
                _order_loadout_match_rows(db, event.id)
            )
            if exception_type
        ],
    )


def _exception_export_rows(
    event_name: str,
    summary: EventSettlementSummaryResponse,
) -> tuple[list[str], list[list[str]]]:
    return (
        [
            "event",
            "exception_type",
            "severity",
            "status",
            "reference_type",
            "reference_id",
            "description",
            "created_at",
        ],
        [
            [
                event_name,
                exception.exception_type,
                exception.severity,
                exception.status,
                exception.reference_type or "",
                exception.reference_id or "",
                exception.description,
                _dt(exception.created_at),
            ]
            for exception in summary.exceptions
        ],
    )


def _order_closeout_export_rows(
    db: Session,
    event: ManagedEvent,
) -> tuple[list[str], list[list[str]]]:
    orders = db.scalars(
        select(EventEntityOrder)
        .where(EventEntityOrder.event_id == event.id)
        .order_by(EventEntityOrder.entity_code, EventEntityOrder.submitted_at)
    ).all()
    rows: list[list[str]] = []
    for order in orders:
        slide = db.get(EventProductSlide, order.slide_id)
        variants = (
            {str(item["model_number"]): item for item in (slide.product_variants or [])}
            if slide
            else {}
        )
        product_lines = (
            [
                (
                    model,
                    str(variants[model]["name"]),
                    quantity,
                    Decimal(str(variants[model]["event_unit_cost"])),
                )
                for model, quantity in order.variant_quantities.items()
                if quantity > 0 and model in variants
            ]
            if variants and order.variant_quantities
            else [
                (
                    slide.model_number if slide else "",
                    slide.name if slide else "",
                    order.quantity,
                    order.unit_cost,
                )
            ]
        )
        for model_number, item_name, quantity, unit_cost in product_lines:
            rows.append(
                [
                    event.name,
                    order.entity_code,
                    slide.vendor_code if slide else "",
                    model_number,
                    item_name,
                    str(quantity),
                    str(unit_cost),
                    str(unit_cost * quantity),
                    order.status,
                    order.review_status,
                    _dt(order.reviewed_at),
                    order.reviewed_by or "",
                    _dt(order.submitted_at),
                    _dt(order.updated_at),
                    "live_presentation",
                    "",
                    "",
                    order.id,
                ]
            )
    for request in _event_buy_fair_requests(db, event.id):
        store = db.scalar(select(Store).where(Store.store_number == request.store_number))
        entity_code = (store.entity_code if store else None) or request.store_number
        for line in request.line_items:
            product = db.scalar(
                select(CatalogProduct).where(CatalogProduct.product_code == line.product_code)
            )
            rows.append(
                [
                    event.name,
                    entity_code,
                    request.vendor_code,
                    product.model_number if product and product.model_number else line.product_code,
                    line.product_name,
                    str(line.quantity),
                    str(line.unit_price),
                    str(line.extended_amount),
                    request.status,
                    "",
                    "",
                    "",
                    _dt(request.created_at),
                    _dt(request.updated_at),
                    "vendor_buy_fair",
                    request.order_number,
                    request.store_number,
                    request.id,
                ]
            )
    rows.sort(key=lambda row: (row[1].casefold(), row[2].casefold(), row[16], row[3].casefold()))
    return (
        [
            "event",
            "entity_code",
            "vendor_code",
            "model_number",
            "item_name",
            "quantity",
            "unit_cost",
            "total_cost",
            "order_status",
            "review_status",
            "reviewed_at",
            "reviewed_by",
            "submitted_at",
            "updated_at",
            "order_channel",
            "order_number",
            "store_number",
            "source_order_id",
        ],
        rows,
    )


def _loadout_closeout_export_rows(
    db: Session,
    event: ManagedEvent,
) -> tuple[list[str], list[list[str]]]:
    assignments = db.scalars(
        select(StoreLoadoutAssignment)
        .where(StoreLoadoutAssignment.event_id == event.id)
        .order_by(
            StoreLoadoutAssignment.store_number,
            StoreLoadoutAssignment.pickup_priority,
        )
    ).all()
    rows: list[list[str]] = []
    for assignment in assignments:
        items = db.scalars(
            select(StoreLoadoutItem)
            .where(StoreLoadoutItem.assignment_id == assignment.id)
            .order_by(StoreLoadoutItem.booth_number, StoreLoadoutItem.item_name)
        ).all()
        if not items:
            rows.append(_loadout_assignment_row(event, assignment, None))
        for item in items:
            rows.append(_loadout_assignment_row(event, assignment, item))
    return (
        [
            "event",
            "store_number",
            "entity_code",
            "assignment_status",
            "loadout_zone",
            "team_name",
            "team_member_emails",
            "team_lead_emails",
            "final_review_requested_at",
            "final_review_requested_by",
            "final_review_completed_at",
            "final_review_completed_by",
            "final_review_notes",
            "recommended_departure_at",
            "signed_at",
            "signed_by",
            "released_at",
            "released_by",
            "booth_number",
            "vendor_code",
            "item_name",
            "model_number",
            "serial_number",
            "quantity_assigned",
            "quantity_found",
            "item_status",
            "damage_notes",
            "missing_notes",
        ],
        rows,
    )


def _loadout_assignment_row(
    event: ManagedEvent,
    assignment: StoreLoadoutAssignment,
    item: StoreLoadoutItem | None,
) -> list[str]:
    return [
        event.name,
        assignment.store_number,
        assignment.entity_code or "",
        assignment.status,
        assignment.loadout_zone or "",
        assignment.team_name or "",
        ", ".join(assignment.team_member_emails or []),
        ", ".join(assignment.team_lead_emails or []),
        _dt(assignment.final_review_requested_at),
        assignment.final_review_requested_by or "",
        _dt(assignment.final_review_completed_at),
        assignment.final_review_completed_by or "",
        assignment.final_review_notes or "",
        _dt(assignment.recommended_departure_at),
        _dt(assignment.signed_at),
        assignment.signed_by or "",
        _dt(assignment.released_at),
        assignment.released_by or "",
        item.booth_number if item else "",
        item.vendor_code if item else "",
        item.item_name if item else "",
        item.model_number or "" if item else "",
        item.serial_number or "" if item else "",
        str(item.quantity_assigned) if item else "",
        str(item.quantity_found) if item else "",
        item.status if item else "",
        item.damage_notes or "" if item else "",
        item.missing_notes or "" if item else "",
    ]


def _feedback_export_rows(
    db: Session,
    event: ManagedEvent,
) -> tuple[list[str], list[list[str]]]:
    rows = db.execute(
        select(EventFeedbackResponse, EventMembership.membership_type)
        .join(EventMembership, EventMembership.user_id == EventFeedbackResponse.user_id)
        .where(EventFeedbackResponse.event_id == event.id, EventMembership.event_id == event.id)
        .order_by(EventFeedbackResponse.created_at)
    ).all()
    return (
        ["event", "attendee_type", "rating", "comments", "submitted_at"],
        [
            [event.name, attendee_type, str(item.rating), item.comments or "", _dt(item.created_at)]
            for item, attendee_type in rows
        ],
    )


def _audit_export_rows(
    db: Session,
    event: ManagedEvent,
) -> tuple[list[str], list[list[str]]]:
    logs = db.scalars(
        select(EventSettlementAuditLog)
        .where(EventSettlementAuditLog.event_id == event.id)
        .order_by(EventSettlementAuditLog.created_at)
    ).all()
    return (
        ["event", "created_at", "action", "actor", "settlement_event_id", "payload"],
        [
            [
                event.name,
                _dt(log.created_at),
                log.action,
                log.actor,
                log.settlement_event_id,
                str(log.payload or {}),
            ]
            for log in logs
        ],
    )


def _dt(value: datetime | None) -> str:
    return value.isoformat() if value else ""
