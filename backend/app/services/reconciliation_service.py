from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.purchase_order import PurchaseOrder
from app.models.receiving import (
    InvoiceReconciliation,
    ReconciliationEvent,
    ReconciliationException,
    VendorInvoice,
    VendorInvoiceLine,
)
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.reconciliation import (
    ReconciliationDecision,
    ReconciliationExceptionResolution,
)
from app.services.snapshot_service import append_snapshot


class ReconciliationError(ValueError):
    pass


def _query():
    return select(InvoiceReconciliation).options(
        selectinload(InvoiceReconciliation.exceptions),
        selectinload(InvoiceReconciliation.events),
    )


def _exception(
    case: InvoiceReconciliation,
    exception_type: str,
    expected: Decimal,
    actual: Decimal,
    invoice_line_id: int | None = None,
) -> None:
    case.exceptions.append(
        ReconciliationException(
            invoice_line_id=invoice_line_id,
            exception_type=exception_type,
            expected_amount=expected,
            actual_amount=actual,
            difference_amount=actual - expected,
            status="open",
        )
    )


def create_reconciliation(
    db: Session, invoice_id: str, actor: str
) -> tuple[InvoiceReconciliation, bool]:
    existing = db.scalar(_query().where(InvoiceReconciliation.invoice_id == invoice_id))
    if existing is not None:
        return existing, False
    invoice = db.scalar(
        select(VendorInvoice)
        .options(selectinload(VendorInvoice.lines).selectinload(VendorInvoiceLine.match))
        .where(VendorInvoice.id == invoice_id)
        .with_for_update()
    )
    if invoice is None:
        raise ReconciliationError("Vendor invoice not found")
    order = db.get(PurchaseOrder, invoice.purchase_order_id)
    if order is None:
        raise ReconciliationError("Purchase order not found")
    case = InvoiceReconciliation(
        invoice_id=invoice.id,
        purchase_order_id=order.id,
        status="ready_for_approval",
        created_by=actor,
    )
    for line in invoice.lines:
        match = line.match
        if match.quantity_difference != 0:
            _exception(
                case,
                "quantity",
                match.accepted_quantity,
                match.invoiced_quantity,
                line.id,
            )
        if match.price_difference != 0:
            _exception(
                case,
                "unit_price",
                match.ordered_unit_price,
                match.invoiced_unit_price,
                line.id,
            )
    if invoice.freight_total != order.freight_total:
        _exception(case, "freight", order.freight_total, invoice.freight_total)
    if invoice.tax_total != order.tax_total:
        _exception(case, "tax", order.tax_total, invoice.tax_total)
    if case.exceptions:
        case.status = "exception_review"
    case.events.append(
        ReconciliationEvent(
            action="create",
            from_status="invoice_received",
            to_status=case.status,
            note=f"Reconciliation created with {len(case.exceptions)} exception(s)",
            actor=actor,
        )
    )
    db.add(case)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(_query().where(InvoiceReconciliation.invoice_id == invoice_id))
        if existing is not None:
            return existing, False
        raise ReconciliationError("Reconciliation conflicts with an existing case") from exc
    db.refresh(case)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="reconciliation.case_created",
            entity_type="invoice_reconciliation",
            entity_id=case.id,
            actor=actor,
            payload={
                "invoice_id": invoice.id,
                "purchase_order_id": order.id,
                "status": case.status,
                "exception_count": len(case.exceptions),
            },
        ),
    )
    return case, True


def resolve_reconciliation_exception(
    db: Session,
    exception_id: str,
    payload: ReconciliationExceptionResolution,
    actor: str,
) -> InvoiceReconciliation:
    item = db.scalar(
        select(ReconciliationException)
        .where(ReconciliationException.id == exception_id)
        .with_for_update()
    )
    if item is None:
        raise ReconciliationError("Reconciliation exception not found")
    case = db.scalar(
        _query().where(InvoiceReconciliation.id == item.reconciliation_id).with_for_update()
    )
    if case is None or case.status != "exception_review":
        raise ReconciliationError("Reconciliation is not accepting exception resolutions")
    if item.status != "open":
        raise ReconciliationError("Reconciliation exception is already closed")
    item.status = "resolved"
    item.disposition = payload.disposition
    item.resolution_note = payload.note
    item.resolved_by = actor
    item.resolved_at = datetime.now(UTC)
    db.flush()
    if all(exception.status != "open" for exception in case.exceptions):
        previous = case.status
        case.status = "ready_for_approval"
        case.events.append(
            ReconciliationEvent(
                action="exceptions_cleared",
                from_status=previous,
                to_status=case.status,
                note="All reconciliation exceptions were dispositioned",
                actor=actor,
            )
        )
    db.commit()
    db.refresh(case)
    return case


def decide_reconciliation(
    db: Session, case_id: str, payload: ReconciliationDecision, actor: str
) -> InvoiceReconciliation:
    case = db.scalar(_query().where(InvoiceReconciliation.id == case_id).with_for_update())
    if case is None:
        raise ReconciliationError("Reconciliation not found")
    if case.status in {"approved", "rejected"}:
        raise ReconciliationError("Reconciliation already has a final decision")
    if payload.action == "approve" and case.status != "ready_for_approval":
        raise ReconciliationError("Open exceptions must be resolved before approval")
    previous = case.status
    invoice = db.get(VendorInvoice, case.invoice_id)
    if invoice is None:
        raise ReconciliationError("Vendor invoice not found")
    if payload.action == "approve":
        if actor in {invoice.received_by, case.created_by}:
            raise ReconciliationError(
                "Payment approval requires an actor independent from invoice intake "
                "and reconciliation"
            )
        case.status = "approved"
        case.approved_by = actor
        case.approved_at = datetime.now(UTC)
        invoice.status = "approved_for_payment"
    else:
        case.status = "rejected"
        case.rejected_by = actor
        case.rejected_at = datetime.now(UTC)
        invoice.status = "rejected"
    case.decision_note = payload.note
    case.events.append(
        ReconciliationEvent(
            action=payload.action,
            from_status=previous,
            to_status=case.status,
            note=payload.note,
            actor=actor,
        )
    )
    db.commit()
    db.refresh(case)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type=f"reconciliation.case_{case.status}",
            entity_type="invoice_reconciliation",
            entity_id=case.id,
            actor=actor,
            payload={"invoice_id": case.invoice_id, "decision": payload.action},
        ),
    )
    return case


def list_reconciliations(db: Session, status: str | None = None) -> list[InvoiceReconciliation]:
    statement = _query().order_by(InvoiceReconciliation.created_at.desc())
    if status is not None:
        statement = statement.where(InvoiceReconciliation.status == status)
    return list(db.scalars(statement).all())
