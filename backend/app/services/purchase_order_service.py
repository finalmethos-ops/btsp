import re
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderSequence,
    PurchaseOrderSource,
)
from app.models.purchasing import PurchaseRequest, PurchaseRequestLineItem
from app.schemas.configuration_entry import ConfigEntryWrite
from app.schemas.event_snapshot import EventSnapshotCreate
from app.services.configuration_service import get_config_entry, upsert_config_entry
from app.services.snapshot_service import append_snapshot

NUMBERING_DEFAULT = {"prefix": "PO", "padding": 6}
GENERATION_DEFAULTS = {
    "numbering": NUMBERING_DEFAULT,
    "consolidation.enabled": {"enabled": True},
    "consolidation.by_store": {"enabled": False},
    "split.max_lines": {"count": 0},
    "split.max_total": {"amount": 0},
}


class PurchaseOrderError(ValueError):
    pass


def seed_purchase_order_defaults(db: Session, actor: str) -> int:
    for key, value in GENERATION_DEFAULTS.items():
        upsert_config_entry(
            db,
            ConfigEntryWrite(
                scope_type="purchase_order",
                scope_key="default",
                key=key,
                value=value,
                description=f"Purchase Order Engine default: {key}.",
                updated_by=actor,
            ),
        )
    return len(GENERATION_DEFAULTS)


def _numbering_config(db: Session) -> tuple[str, int]:
    entry = get_config_entry(db, "purchase_order", "default", "numbering")
    value = NUMBERING_DEFAULT if entry is None else entry.value
    prefix = value.get("prefix")
    padding = value.get("padding")
    if (
        not isinstance(prefix, str)
        or re.fullmatch(r"[A-Z0-9-]{1,24}", prefix) is None
        or not isinstance(padding, int)
        or not 4 <= padding <= 12
    ):
        raise PurchaseOrderError("Purchase order numbering configuration is invalid")
    return prefix, padding


def allocate_po_number(db: Session, at: datetime | None = None) -> str:
    prefix, padding = _numbering_config(db)
    year = (at or datetime.now(UTC)).year
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"purchase-order:{prefix}:{year}"},
        )
    sequence = db.scalar(
        select(PurchaseOrderSequence)
        .where(
            PurchaseOrderSequence.prefix == prefix,
            PurchaseOrderSequence.sequence_year == year,
        )
        .with_for_update()
    )
    if sequence is None:
        sequence = PurchaseOrderSequence(prefix=prefix, sequence_year=year, next_value=1)
        db.add(sequence)
        db.flush()
    value = sequence.next_value
    sequence.next_value += 1
    return f"{prefix}-{year}-{value:0{padding}d}"


def _required_permission(workflow_code: str) -> str:
    if workflow_code == "BPP_PURCHASING":
        return "workflow.bpp.po_generate"
    if workflow_code == "IND_PURCHASING":
        return "workflow.ind.review"
    raise PurchaseOrderError(f"Unsupported purchasing workflow: {workflow_code}")


def _generation_config(db: Session) -> tuple[bool, bool, int, Decimal]:
    values = {key: default for key, default in GENERATION_DEFAULTS.items()}
    for key in values:
        entry = get_config_entry(db, "purchase_order", "default", key)
        if entry is not None:
            values[key] = entry.value
    consolidation = values["consolidation.enabled"].get("enabled")
    by_store = values["consolidation.by_store"].get("enabled")
    max_lines = values["split.max_lines"].get("count")
    try:
        max_total = Decimal(str(values["split.max_total"].get("amount")))
    except (InvalidOperation, ValueError, TypeError):
        max_total = Decimal("-1")
    if not isinstance(consolidation, bool) or not isinstance(by_store, bool):
        raise PurchaseOrderError("Purchase order consolidation configuration is invalid")
    if isinstance(max_lines, bool) or not isinstance(max_lines, int) or max_lines < 0:
        raise PurchaseOrderError("Purchase order maximum line configuration is invalid")
    if max_total < 0:
        raise PurchaseOrderError("Purchase order maximum total configuration is invalid")
    return consolidation, by_store, max_lines, max_total


def _partition_lines(
    lines: list[tuple[PurchaseRequest, PurchaseRequestLineItem]],
    max_lines: int,
    max_total: Decimal,
) -> list[list[tuple[PurchaseRequest, PurchaseRequestLineItem]]]:
    partitions: list[list[tuple[PurchaseRequest, PurchaseRequestLineItem]]] = []
    current: list[tuple[PurchaseRequest, PurchaseRequestLineItem]] = []
    current_total = Decimal("0")
    for source, line in lines:
        line_total = line.extended_amount
        exceeds_lines = max_lines > 0 and len(current) >= max_lines
        exceeds_total = max_total > 0 and current and current_total + line_total > max_total
        if exceeds_lines or exceeds_total:
            partitions.append(current)
            current = []
            current_total = Decimal("0")
        current.append((source, line))
        current_total += line_total
    if current:
        partitions.append(current)
    return partitions


def generate_purchase_orders(
    db: Session,
    purchase_request_ids: list[str],
    actor: str,
    permission_codes: set[str],
) -> list[PurchaseOrder]:
    unique_ids = list(dict.fromkeys(purchase_request_ids))
    loaded_requests = list(
        db.scalars(
            select(PurchaseRequest)
            .options(selectinload(PurchaseRequest.line_items))
            .where(PurchaseRequest.id.in_(unique_ids))
        ).all()
    )
    if len(loaded_requests) != len(unique_ids):
        raise PurchaseOrderError("One or more purchase requests were not found")
    requests_by_id = {request.id: request for request in loaded_requests}
    requests = [requests_by_id[request_id] for request_id in unique_ids]
    existing_ids = set(
        db.scalars(
            select(PurchaseOrderSource.purchase_request_id).where(
                PurchaseOrderSource.purchase_request_id.in_(unique_ids)
            )
        ).all()
    )
    if existing_ids:
        raise PurchaseOrderError("A purchase order already exists for a source request")
    consolidation_enabled, consolidation_by_store, max_lines, max_total = _generation_config(db)
    grouped: dict[tuple[str, str, str, str, str], list[PurchaseRequest]] = defaultdict(list)
    for request in requests:
        if request.status != "po_created":
            raise PurchaseOrderError(
                f"Purchase request {request.id} is not eligible for PO generation"
            )
        required = _required_permission(request.workflow_code)
        if required not in permission_codes:
            raise PermissionError(required)
        if not request.line_items:
            raise PurchaseOrderError(f"Purchase request {request.id} has no line items")
        group_marker = "consolidated" if consolidation_enabled else request.id
        store_marker = request.store_number if consolidation_by_store else "all-stores"
        grouped[
            (
                request.workflow_code,
                request.vendor_code,
                request.currency,
                group_marker,
                store_marker,
            )
        ].append(request)

    orders: list[PurchaseOrder] = []
    for (
        workflow_code,
        vendor_code,
        currency,
        _group_marker,
        _store_marker,
    ), sources in grouped.items():
        source_lines = [(source, line) for source in sources for line in source.line_items]
        for partition in _partition_lines(source_lines, max_lines, max_total):
            subtotal = sum(
                (line.quantity * line.unit_price for _source, line in partition),
                Decimal("0"),
            )
            freight = sum((line.freight_amount for _source, line in partition), Decimal("0"))
            tax = sum((line.tax_amount for _source, line in partition), Decimal("0"))
            order = PurchaseOrder(
                po_number=allocate_po_number(db),
                workflow_code=workflow_code,
                vendor_code=vendor_code,
                status="created",
                currency=currency,
                subtotal=subtotal,
                freight_total=freight,
                tax_total=tax,
                total=subtotal + freight + tax,
                created_by=actor,
            )
            db.add(order)
            partition_sources: dict[str, PurchaseRequest] = {
                source.id: source for source, _line in partition
            }
            for source in partition_sources.values():
                order.sources.append(
                    PurchaseOrderSource(
                        purchase_request_id=source.id,
                        store_number=source.store_number,
                    )
                )
            for source, line in partition:
                order.lines.append(
                    PurchaseOrderLine(
                        source_request_id=source.id,
                        source_line_id=line.id,
                        store_number=source.store_number,
                        product_code=line.product_code,
                        product_name=line.product_name,
                        quantity=line.quantity,
                        unit_price=line.unit_price,
                        freight_amount=line.freight_amount,
                        tax_amount=line.tax_amount,
                        extended_amount=line.extended_amount,
                        notes=line.notes,
                    )
                )
            orders.append(order)
    db.commit()
    for order in orders:
        db.refresh(order)
        append_snapshot(
            db,
            EventSnapshotCreate(
                event_type="purchase_order.created",
                entity_type="purchase_order",
                entity_id=order.id,
                actor=actor,
                payload={
                    "po_number": order.po_number,
                    "workflow_code": order.workflow_code,
                    "vendor_code": order.vendor_code,
                    "source_request_ids": [source.purchase_request_id for source in order.sources],
                    "total": str(order.total),
                },
            ),
        )
    return orders


def list_purchase_orders(db: Session, allowed_workflows: set[str]) -> list[PurchaseOrder]:
    statement = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.sources), selectinload(PurchaseOrder.lines))
        .order_by(PurchaseOrder.created_at.desc())
    )
    if allowed_workflows:
        statement = statement.where(PurchaseOrder.workflow_code.in_(allowed_workflows))
    return list(db.scalars(statement).unique().all())


def get_purchase_order(db: Session, order_id: str) -> PurchaseOrder | None:
    return db.scalar(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.sources), selectinload(PurchaseOrder.lines))
        .where(PurchaseOrder.id == order_id)
    )
