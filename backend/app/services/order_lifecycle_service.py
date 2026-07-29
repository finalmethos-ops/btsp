from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import CatalogProduct
from app.models.event_snapshot import EventSnapshot
from app.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderAttention,
    PurchaseOrderLine,
    PurchaseOrderSource,
)
from app.models.purchasing import PurchaseRequest, PurchaseRequestLineItem
from app.schemas.order_lifecycle import LifecycleLineWrite
from app.services.purchase_order_filter_service import apply_purchase_order_filters
from app.services.purchase_order_service import allocate_po_number
from app.services.purchase_request_service import _validate_references, build_order_number
from app.services.vendor_moq_service import evaluate_vendor_moq


class OrderLifecycleError(ValueError):
    pass


def _request_query():
    return select(PurchaseRequest).options(
        selectinload(PurchaseRequest.line_items).selectinload(
            PurchaseRequestLineItem.catalog_product
        )
    )


def _order_query():
    return select(PurchaseOrder).options(
        selectinload(PurchaseOrder.sources),
        selectinload(PurchaseOrder.lines),
        selectinload(PurchaseOrder.attention_items),
    )


def _recalculate(request: PurchaseRequest) -> None:
    request.subtotal = sum(
        (line.quantity * line.unit_price for line in request.line_items), Decimal("0")
    )
    request.freight_total = sum((line.freight_amount for line in request.line_items), Decimal("0"))
    request.tax_total = sum((line.tax_amount for line in request.line_items), Decimal("0"))
    request.total = request.subtotal + request.freight_total + request.tax_total


def create_vendor_request(
    db: Session,
    vendor_code: str,
    store_number: str,
    actor: str,
    expected_delivery_date: date | None = None,
) -> PurchaseRequest:
    return create_vendor_requests(
        db,
        vendor_code,
        [store_number],
        actor,
        expected_delivery_date,
    )[0]


def create_vendor_requests(
    db: Session,
    vendor_code: str,
    store_numbers: list[str],
    actor: str,
    expected_delivery_date: date | None = None,
    line_items: list[LifecycleLineWrite] | None = None,
    order_metadata_factory: Callable[[str], tuple[str, dict[str, Any]]] | None = None,
) -> list[PurchaseRequest]:
    unique_store_numbers = list(dict.fromkeys(store_numbers))
    if not unique_store_numbers:
        raise OrderLifecycleError("Select at least one store")
    try:
        for store_number in unique_store_numbers:
            _validate_references(db, store_number, vendor_code)
    except ValueError as exc:
        raise OrderLifecycleError(str(exc)) from exc
    if line_items is not None and not line_items:
        raise OrderLifecycleError("Add at least one model to the cart")
    product_codes = [line.product_code for line in line_items or []]
    if len(product_codes) != len(set(product_codes)):
        raise OrderLifecycleError("Each model may appear only once in the cart")
    products = {
        product.product_code: product
        for product in db.scalars(
            select(CatalogProduct).where(
                CatalogProduct.product_code.in_(product_codes),
                CatalogProduct.vendor_code == vendor_code,
                CatalogProduct.is_active.is_(True),
                CatalogProduct.is_available.is_(True),
            )
        )
    }
    missing = [code for code in product_codes if code not in products]
    if missing:
        raise OrderLifecycleError(f"Model is not available for this vendor: {missing[0]}")
    requests = []
    for store_number in unique_store_numbers:
        order_number, context = (
            order_metadata_factory(store_number)
            if order_metadata_factory
            else (build_order_number(db, store_number, vendor_code), {})
        )
        requests.append(
            PurchaseRequest(
                order_number=order_number,
                workflow_code="VENDOR_ORDER",
                store_number=store_number,
                vendor_code=vendor_code,
                status="vendor_draft",
                expected_delivery_date=expected_delivery_date,
                context=context,
                created_by=actor,
                updated_by=actor,
            )
        )
    for request in requests:
        for line in line_items or []:
            product = products[line.product_code]
            request.line_items.append(
                PurchaseRequestLineItem(
                    product_code=product.product_code,
                    product_name=product.name,
                    quantity=line.quantity,
                    unit_price=product.unit_price,
                    freight_amount=Decimal("0"),
                    tax_amount=Decimal("0"),
                    extended_amount=line.quantity * product.unit_price,
                    notes=line.notes,
                )
            )
        _recalculate(request)
    db.add_all(requests)
    db.commit()
    for request in requests:
        db.refresh(request)
    return requests


def delete_vendor_request(db: Session, request: PurchaseRequest) -> None:
    if request.status != "vendor_draft":
        raise OrderLifecycleError("Only unsubmitted vendor drafts can be deleted")
    db.delete(request)
    db.commit()


def update_vendor_request_date(
    db: Session, request: PurchaseRequest, expected_delivery_date: date, actor: str
) -> PurchaseRequest:
    if request.status != "vendor_draft":
        raise OrderLifecycleError("Only unsubmitted vendor drafts can be changed")
    request.expected_delivery_date = expected_delivery_date
    request.updated_by = actor
    request.revision += 1
    db.commit()
    return get_request(db, request.id) or request


def list_vendor_requests(db: Session, vendor_code: str) -> list[PurchaseRequest]:
    return list(
        db.scalars(
            _request_query()
            .where(
                PurchaseRequest.workflow_code == "VENDOR_ORDER",
                PurchaseRequest.vendor_code == vendor_code,
                PurchaseRequest.status.in_({"vendor_draft", "submitted_to_purchasing"}),
            )
            .order_by(PurchaseRequest.created_at.desc())
        )
        .unique()
        .all()
    )


def list_purchasing_requests(db: Session) -> list[PurchaseRequest]:
    return list(
        db.scalars(
            _request_query()
            .where(
                PurchaseRequest.workflow_code == "VENDOR_ORDER",
                PurchaseRequest.status == "submitted_to_purchasing",
            )
            .order_by(PurchaseRequest.created_at)
        )
        .unique()
        .all()
    )


def get_request(db: Session, request_id: str) -> PurchaseRequest | None:
    return db.scalar(_request_query().where(PurchaseRequest.id == request_id))


def write_request_line(
    db: Session,
    request: PurchaseRequest,
    payload: LifecycleLineWrite,
    actor: str,
    line_id: int | None = None,
) -> PurchaseRequest:
    if request.status not in {"vendor_draft", "submitted_to_purchasing"}:
        raise OrderLifecycleError("Order request is no longer editable")
    product = db.scalar(
        select(CatalogProduct).where(
            CatalogProduct.product_code == payload.product_code,
            CatalogProduct.vendor_code == request.vendor_code,
            CatalogProduct.is_active.is_(True),
            CatalogProduct.is_available.is_(True),
        )
    )
    if product is None:
        raise OrderLifecycleError("Model is not available for this vendor")
    line = next((item for item in request.line_items if item.id == line_id), None)
    if line_id is not None and line is None:
        raise OrderLifecycleError("Order request line was not found")
    values = dict(
        product_code=product.product_code,
        product_name=product.name,
        quantity=payload.quantity,
        unit_price=product.unit_price,
        freight_amount=Decimal("0"),
        tax_amount=Decimal("0"),
        extended_amount=payload.quantity * product.unit_price,
        notes=payload.notes,
    )
    if line is None:
        request.line_items.append(PurchaseRequestLineItem(**values))
    else:
        for key, value in values.items():
            setattr(line, key, value)
    _recalculate(request)
    request.updated_by = actor
    request.revision += 1
    db.commit()
    db.refresh(request)
    return get_request(db, request.id) or request


def remove_request_line(
    db: Session, request: PurchaseRequest, line_id: int, actor: str
) -> PurchaseRequest:
    if request.status not in {"vendor_draft", "submitted_to_purchasing"}:
        raise OrderLifecycleError("Order request is no longer editable")
    line = next((item for item in request.line_items if item.id == line_id), None)
    if line is None:
        raise OrderLifecycleError("Order request line was not found")
    request.line_items.remove(line)
    db.flush()
    _recalculate(request)
    request.updated_by = actor
    request.revision += 1
    db.commit()
    return get_request(db, request.id) or request


def submit_vendor_request(db: Session, request: PurchaseRequest, actor: str) -> PurchaseRequest:
    if request.status != "vendor_draft":
        raise OrderLifecycleError("Only vendor drafts can be submitted")
    if not request.line_items:
        raise OrderLifecycleError("Order request must contain at least one model")
    if request.expected_delivery_date is None:
        raise OrderLifecycleError("Order request requires an expected delivery date")
    issues = evaluate_vendor_moq(db, request)
    if issues:
        raise OrderLifecycleError("; ".join(issue.message for issue in issues))
    request.status = "submitted_to_purchasing"
    request.updated_by = actor
    db.commit()
    db.refresh(request)
    return request


def decide_request(
    db: Session,
    request: PurchaseRequest,
    action: str,
    reason: str | None,
    actor: str,
    expected_delivery_date: date | None = None,
) -> PurchaseOrder | None:
    if request.status != "submitted_to_purchasing":
        raise OrderLifecycleError("Order request is not awaiting Purchasing review")
    if action == "cancel":
        request.status = "cancelled_by_purchasing"
        request.context = {**request.context, "cancellation_reason": reason or ""}
        request.updated_by = actor
        db.commit()
        return None
    if not request.line_items:
        raise OrderLifecycleError("Order request cannot be approved without models")
    if expected_delivery_date is not None:
        request.expected_delivery_date = expected_delivery_date
    if request.expected_delivery_date is None:
        raise OrderLifecycleError("PO approval requires an expected delivery date")
    issues = evaluate_vendor_moq(db, request)
    if issues:
        raise OrderLifecycleError(
            "PO approval blocked by vendor MOQ: " + "; ".join(issue.message for issue in issues)
        )
    order = PurchaseOrder(
        po_number=allocate_po_number(db, request.store_number),
        workflow_code="VENDOR_ORDER",
        vendor_code=request.vendor_code,
        status="awaiting_vendor_acceptance",
        currency=request.currency,
        subtotal=request.subtotal,
        freight_total=request.freight_total,
        tax_total=request.tax_total,
        total=request.total,
        expected_delivery_date=request.expected_delivery_date,
        created_by=actor,
    )
    order.sources.append(
        PurchaseOrderSource(purchase_request_id=request.id, store_number=request.store_number)
    )
    for line in request.line_items:
        order.lines.append(
            PurchaseOrderLine(
                source_request_id=request.id,
                source_line_id=line.id,
                store_number=request.store_number,
                product_code=line.product_code,
                product_name=line.product_name,
                quantity=line.quantity,
                received_quantity=0,
                unit_price=line.unit_price,
                freight_amount=line.freight_amount,
                tax_amount=line.tax_amount,
                extended_amount=line.extended_amount,
                notes=line.notes,
            )
        )
    request.status = "approved_to_po"
    request.updated_by = actor
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def list_vendor_pos(
    db: Session,
    vendor_code: str,
    queue: str,
    **filters,
) -> list[PurchaseOrder]:
    statuses = {
        "pending": {"awaiting_vendor_acceptance"},
        "active": {"active"},
        "attention": {"vendor_attention"},
        "rejected": {"vendor_rejected"},
    }.get(queue, {"awaiting_vendor_acceptance"})
    statement = _order_query().where(
        PurchaseOrder.vendor_code == vendor_code, PurchaseOrder.status.in_(statuses)
    )
    statement = apply_purchase_order_filters(statement, **filters)
    return list(db.scalars(statement.order_by(PurchaseOrder.updated_at.desc())).unique().all())


def respond_to_po(
    db: Session,
    order: PurchaseOrder,
    action: str,
    eta,
    reason: str | None,
    actor: str,
) -> PurchaseOrder:
    if order.status != "awaiting_vendor_acceptance":
        raise OrderLifecycleError("PO is not awaiting vendor acceptance")
    if action == "accept" and order.expected_delivery_date and eta < order.expected_delivery_date:
        raise OrderLifecycleError("Vendor ETA cannot be earlier than the PO expected delivery date")
    order.vendor_response_at = datetime.now(UTC)
    if action == "accept":
        order.status = "active"
        order.vendor_eta = eta
        order.vendor_rejection_reason = None
    else:
        order.status = "vendor_rejected"
        order.vendor_rejection_reason = (reason or "").strip()
    db.add(
        EventSnapshot(
            event_type=f"purchase_order.vendor_{action}",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload={"eta": str(eta) if eta else None, "reason": reason},
        )
    )
    db.commit()
    db.refresh(order)
    return order


def list_purchasing_pos(db: Session, queue: str, **filters) -> list[PurchaseOrder]:
    statuses = {
        "active": {"active"},
        "attention": {"purchasing_attention"},
        "rejected": {"vendor_rejected"},
        "inactive": {"cancelled"},
    }.get(queue, {"active"})
    statement = _order_query().where(
        PurchaseOrder.workflow_code == "VENDOR_ORDER",
        PurchaseOrder.status.in_(statuses),
    )
    statement = apply_purchase_order_filters(statement, **filters)
    return list(db.scalars(statement.order_by(PurchaseOrder.updated_at.desc())).unique().all())


def update_active_po_eta(db: Session, order: PurchaseOrder, eta: date, actor: str) -> PurchaseOrder:
    if order.status != "active":
        raise OrderLifecycleError("Only active POs allow a global ETA update")
    if order.expected_delivery_date and eta < order.expected_delivery_date:
        raise OrderLifecycleError("ETA cannot be earlier than the PO expected delivery date")
    previous_eta = order.vendor_eta
    order.vendor_eta = eta
    db.add(
        EventSnapshot(
            event_type="purchase_order.eta_updated",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload={"eta": eta.isoformat()},
        )
    )
    performance_event = "delay" if previous_eta is not None and eta > previous_eta else "eta_update"
    db.add(
        EventSnapshot(
            event_type=f"vendor.fulfillment.{performance_event}_reported",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload={
                "vendor_code": order.vendor_code,
                "po_number": order.po_number,
                "performance_event": performance_event,
                "previous_eta": previous_eta.isoformat() if previous_eta else None,
                "new_eta": eta.isoformat(),
            },
        )
    )
    db.commit()
    return get_order(db, order.id) or order


def get_order(db: Session, order_id: str) -> PurchaseOrder | None:
    return db.scalar(
        _order_query().where(PurchaseOrder.id == order_id).execution_options(populate_existing=True)
    )


def create_vendor_po_issue(
    db: Session,
    order: PurchaseOrder,
    action: str,
    line_id: int,
    quantity: Decimal,
    eta: date | None,
    substitute_product_code: str | None,
    reason: str | None,
    actor: str,
) -> PurchaseOrder:
    if order.status not in {"active", "purchasing_attention"}:
        raise OrderLifecycleError("Only active POs can report fulfillment issues")
    line = next((item for item in order.lines if item.id == line_id), None)
    if line is None:
        raise OrderLifecycleError("PO line was not found")
    if quantity > line.quantity - line.received_quantity:
        raise OrderLifecycleError("Affected units cannot exceed unreceived units")
    substitute = None
    if substitute_product_code:
        substitute = db.scalar(
            select(CatalogProduct).where(
                CatalogProduct.product_code == substitute_product_code,
                CatalogProduct.vendor_code == order.vendor_code,
                CatalogProduct.is_active.is_(True),
                CatalogProduct.is_available.is_(True),
            )
        )
        if substitute is None:
            raise OrderLifecycleError("Suggested substitute is not an available vendor model")
    attention = PurchaseOrderAttention(
        purchase_order_id=order.id,
        initiated_by_side="vendor",
        action_type=action,
        status="pending",
        payload={
            "line_id": line_id,
            "product_code": line.product_code,
            "quantity": str(quantity),
            "eta": eta.isoformat() if eta else None,
            "substitute_product_code": substitute_product_code,
            "substitute_product_name": substitute.name if substitute else None,
            "substitute_unit_price": str(substitute.unit_price) if substitute else None,
        },
        reason=reason,
        created_by=actor,
    )
    order.status = "purchasing_attention"
    db.add(attention)
    db.flush()
    event_payload = {
        "vendor_code": order.vendor_code,
        "po_number": order.po_number,
        "attention_id": attention.id,
        "performance_event": action,
        "line_id": line_id,
        "product_code": line.product_code,
        "quantity": str(quantity),
        "eta": eta.isoformat() if eta else None,
        "substitute_product_code": substitute_product_code,
        "reason": reason,
    }
    db.add(
        EventSnapshot(
            event_type=f"vendor.fulfillment.{action}_reported",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload=event_payload,
        )
    )
    if substitute is not None:
        db.add(
            EventSnapshot(
                event_type="vendor.fulfillment.substitution_proposed",
                entity_type="purchase_order",
                entity_id=order.id,
                actor=actor,
                payload={
                    **event_payload,
                    "performance_event": "substitution",
                    "substitute_product_name": substitute.name,
                    "substitute_unit_price": str(substitute.unit_price),
                },
            )
        )
    db.commit()
    return get_order(db, order.id) or order


def list_substitute_options(
    db: Session, order: PurchaseOrder, line_id: int
) -> list[CatalogProduct]:
    line = next((item for item in order.lines if item.id == line_id), None)
    if line is None:
        raise OrderLifecycleError("PO line was not found")
    original = db.scalar(
        select(CatalogProduct).where(
            CatalogProduct.product_code == line.product_code,
            CatalogProduct.vendor_code == order.vendor_code,
        )
    )
    if original is None:
        raise OrderLifecycleError("Original PO model is no longer in the vendor catalog")
    return list(
        db.scalars(
            select(CatalogProduct)
            .where(
                CatalogProduct.vendor_code == order.vendor_code,
                CatalogProduct.product_code != line.product_code,
                CatalogProduct.moq_rule_id == original.moq_rule_id,
                CatalogProduct.unit_price >= line.unit_price,
                CatalogProduct.is_active.is_(True),
                CatalogProduct.is_available.is_(True),
            )
            .order_by(CatalogProduct.unit_price, CatalogProduct.name)
        ).all()
    )


def create_purchasing_po_change(
    db: Session,
    order: PurchaseOrder,
    action: str,
    actor: str,
    reason: str,
    line_id: int | None = None,
    product_code: str | None = None,
    quantity: Decimal | None = None,
    requested_date: date | None = None,
) -> PurchaseOrder:
    if order.status != "active":
        raise OrderLifecycleError("Only active POs can receive a change request")
    if line_id is not None and not any(line.id == line_id for line in order.lines):
        raise OrderLifecycleError("PO line was not found")
    if product_code:
        product = db.scalar(
            select(CatalogProduct).where(
                CatalogProduct.product_code == product_code,
                CatalogProduct.vendor_code == order.vendor_code,
                CatalogProduct.is_active.is_(True),
                CatalogProduct.is_available.is_(True),
            )
        )
        if product is None:
            raise OrderLifecycleError("Model is not available from this PO vendor")
    attention = PurchaseOrderAttention(
        purchase_order_id=order.id,
        initiated_by_side="purchasing",
        action_type=action,
        status="pending",
        payload={
            "line_id": line_id,
            "product_code": product_code,
            "quantity": str(quantity) if quantity is not None else None,
            "requested_date": requested_date.isoformat() if requested_date else None,
        },
        reason=reason,
        created_by=actor,
    )
    order.status = "vendor_attention"
    db.add(attention)
    db.commit()
    return get_order(db, order.id) or order


def _validate_po_moq(db: Session, order: PurchaseOrder, quantities: dict[str, Decimal]) -> None:
    products = {
        product.product_code: product
        for product in db.scalars(
            select(CatalogProduct).where(CatalogProduct.product_code.in_(quantities))
        ).all()
    }
    request_like = SimpleNamespace(
        vendor_code=order.vendor_code,
        line_items=[
            SimpleNamespace(
                quantity=quantity,
                unit_price=products[code].unit_price,
                catalog_product=products[code],
            )
            for code, quantity in quantities.items()
            if quantity > 0 and code in products
        ],
    )
    issues = evaluate_vendor_moq(db, request_like)
    if issues:
        raise OrderLifecycleError("; ".join(issue.message for issue in issues))


def _recalculate_po(order: PurchaseOrder) -> None:
    order.subtotal = sum((line.quantity * line.unit_price for line in order.lines), Decimal("0"))
    order.freight_total = sum((line.freight_amount for line in order.lines), Decimal("0"))
    order.tax_total = sum((line.tax_amount for line in order.lines), Decimal("0"))
    for line in order.lines:
        line.extended_amount = (
            line.quantity * line.unit_price + line.freight_amount + line.tax_amount
        )
    order.total = order.subtotal + order.freight_total + order.tax_total


def _queue_vendor_change_confirmation(
    db: Session,
    order: PurchaseOrder,
    original_attention: PurchaseOrderAttention,
    actor: str,
    resolution_action: str,
    change_details: dict,
) -> None:
    payload = {
        "original_attention_id": original_attention.id,
        "original_action": original_attention.action_type,
        "resolution_action": resolution_action,
        "approved_by": actor,
        "approved_at": datetime.now(UTC).isoformat(),
        "original_request": dict(original_attention.payload),
        "change_details": change_details,
    }
    db.add(
        PurchaseOrderAttention(
            purchase_order_id=order.id,
            initiated_by_side="purchasing",
            action_type="vendor_change_confirmation",
            status="pending",
            payload=payload,
            reason=(
                "Purchasing applied this vendor-submitted PO change. "
                "Vendor confirmation is required."
            ),
            created_by=actor,
        )
    )
    db.add(
        EventSnapshot(
            event_type="purchase_order.vendor_change_approved",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload=payload,
        )
    )


def _apply_approved_substitution(
    db: Session,
    order: PurchaseOrder,
    attention: PurchaseOrderAttention,
) -> dict:
    payload = attention.payload
    substitute_code = payload.get("substitute_product_code")
    if attention.action_type != "out_of_stock" or not substitute_code:
        return {"po_line_changed": False}
    line = next((item for item in order.lines if item.id == int(payload["line_id"])), None)
    if line is None:
        raise OrderLifecycleError("PO line was not found")
    substitute = db.scalar(
        select(CatalogProduct).where(
            CatalogProduct.product_code == substitute_code,
            CatalogProduct.vendor_code == order.vendor_code,
            CatalogProduct.is_active.is_(True),
            CatalogProduct.is_available.is_(True),
        )
    )
    if substitute is None:
        raise OrderLifecycleError("Suggested substitute is no longer available")
    quantity = Decimal(payload["quantity"])
    remaining = line.quantity - quantity
    if remaining < line.received_quantity:
        raise OrderLifecycleError("Cannot substitute units already received")
    quantities = {item.product_code: item.quantity for item in order.lines}
    quantities[line.product_code] = remaining
    quantities[substitute.product_code] = (
        quantities.get(substitute.product_code, Decimal("0")) + quantity
    )
    _validate_po_moq(db, order, quantities)
    original = {
        "product_code": line.product_code,
        "product_name": line.product_name,
        "quantity_before": str(line.quantity),
        "quantity_after": str(remaining),
    }
    if remaining == 0:
        order.lines.remove(line)
    else:
        line.quantity = remaining
    existing = next(
        (item for item in order.lines if item.product_code == substitute.product_code),
        None,
    )
    if existing:
        existing.quantity += quantity
    else:
        order.lines.append(
            PurchaseOrderLine(
                source_request_id=order.sources[0].purchase_request_id,
                source_line_id=None,
                store_number=order.sources[0].store_number,
                product_code=substitute.product_code,
                product_name=substitute.name,
                quantity=quantity,
                received_quantity=0,
                unit_price=substitute.unit_price,
                freight_amount=0,
                tax_amount=0,
                extended_amount=quantity * substitute.unit_price,
                notes=f"Vendor substitute approved for {original['product_code']}",
            )
        )
    _recalculate_po(order)
    return {
        "po_line_changed": True,
        "original": original,
        "substitute": {
            "product_code": substitute.product_code,
            "product_name": substitute.name,
            "quantity": str(quantity),
            "unit_price": str(substitute.unit_price),
        },
    }


def respond_to_attention(
    db: Session,
    order: PurchaseOrder,
    attention_id: str,
    action: str,
    actor_side: str,
    actor: str,
    eta: date | None = None,
    note: str | None = None,
) -> PurchaseOrder:
    attention = next((item for item in order.attention_items if item.id == attention_id), None)
    if attention is None or attention.status != "pending":
        raise OrderLifecycleError("Pending attention item was not found")
    expected_side = "vendor" if attention.initiated_by_side == "purchasing" else "purchasing"
    if actor_side != expected_side:
        raise OrderLifecycleError("This attention item belongs to the other party")
    if actor_side == "purchasing" and action != "acknowledge":
        raise OrderLifecycleError("Purchasing must acknowledge vendor fulfillment issues")
    if (
        actor_side == "vendor"
        and attention.action_type == "vendor_change_confirmation"
        and action != "confirm"
    ):
        raise OrderLifecycleError("Vendor must confirm this applied PO change")
    if (
        actor_side == "vendor"
        and attention.action_type != "vendor_change_confirmation"
        and action not in {"accept", "deny"}
    ):
        raise OrderLifecycleError("Vendor must accept or deny the requested change")

    if action == "accept":
        payload = attention.payload
        if attention.action_type == "cancel":
            received = sum((line.received_quantity for line in order.lines), Decimal("0"))
            order.status = "awaiting_reconciliation" if received > 0 else "cancelled"
        elif attention.action_type == "add_model":
            product = db.scalar(
                select(CatalogProduct).where(CatalogProduct.product_code == payload["product_code"])
            )
            if product is None:
                raise OrderLifecycleError("Requested model is no longer available")
            quantity = Decimal(payload["quantity"])
            quantities = {line.product_code: line.quantity for line in order.lines}
            quantities[product.product_code] = (
                quantities.get(product.product_code, Decimal("0")) + quantity
            )
            _validate_po_moq(db, order, quantities)
            existing = next(
                (line for line in order.lines if line.product_code == product.product_code), None
            )
            if existing:
                existing.quantity += quantity
            else:
                order.lines.append(
                    PurchaseOrderLine(
                        source_request_id=order.sources[0].purchase_request_id,
                        source_line_id=None,
                        store_number=order.sources[0].store_number,
                        product_code=product.product_code,
                        product_name=product.name,
                        quantity=quantity,
                        received_quantity=0,
                        unit_price=product.unit_price,
                        freight_amount=0,
                        tax_amount=0,
                        extended_amount=quantity * product.unit_price,
                    )
                )
            order.status = "active"
            _recalculate_po(order)
        elif attention.action_type == "remove_units":
            line = next((item for item in order.lines if item.id == payload["line_id"]), None)
            if line is None:
                raise OrderLifecycleError("PO line was not found")
            remaining = line.quantity - Decimal(payload["quantity"])
            if remaining < line.received_quantity or remaining < 0:
                raise OrderLifecycleError("Cannot remove units already received")
            quantities = {item.product_code: item.quantity for item in order.lines}
            quantities[line.product_code] = remaining
            _validate_po_moq(db, order, quantities)
            if remaining == 0:
                order.lines.remove(line)
            else:
                line.quantity = remaining
            order.status = "active"
            _recalculate_po(order)
        elif attention.action_type in {"delay", "expedite"}:
            order.expected_delivery_date = date.fromisoformat(payload["requested_date"])
            if eta is not None:
                order.vendor_eta = eta
            order.status = "active"
        elif attention.action_type == "request_eta":
            if eta is None:
                raise OrderLifecycleError("Accepting an ETA request requires a new ETA")
            if order.expected_delivery_date and eta < order.expected_delivery_date:
                raise OrderLifecycleError("ETA cannot be earlier than the expected delivery date")
            order.vendor_eta = eta
            order.status = "active"
    elif action == "deny":
        order.status = "active"

    attention.status = {
        "accept": "accepted",
        "deny": "denied",
        "acknowledge": "acknowledged",
        "confirm": "confirmed",
    }[action]
    attention.response_note = note
    attention.responded_by = actor
    attention.responded_at = datetime.now(UTC)
    if action == "acknowledge":
        change_details = _apply_approved_substitution(db, order, attention)
        resolution_action = (
            "approved_substitution"
            if change_details.get("po_line_changed")
            else f"approved_{attention.action_type}"
        )
        _queue_vendor_change_confirmation(
            db,
            order,
            attention,
            actor,
            resolution_action,
            change_details,
        )
        other_pending = any(
            item.id != attention.id
            and item.status == "pending"
            and item.initiated_by_side == "vendor"
            for item in order.attention_items
        )
        order.status = "purchasing_attention" if other_pending else "vendor_attention"
    elif action == "confirm":
        db.add(
            EventSnapshot(
                event_type="purchase_order.vendor_change_confirmed",
                entity_type="purchase_order",
                entity_id=order.id,
                actor=actor,
                payload={
                    **attention.payload,
                    "confirmation_attention_id": attention.id,
                    "confirmed_at": attention.responded_at.isoformat(),
                    "confirmation_note": note,
                },
            )
        )
        pending_confirmations = any(
            item.id != attention.id
            and item.status == "pending"
            and item.action_type == "vendor_change_confirmation"
            for item in order.attention_items
        )
        pending_vendor_issues = any(
            item.status == "pending" and item.initiated_by_side == "vendor"
            for item in order.attention_items
        )
        order.status = (
            "vendor_attention"
            if pending_confirmations
            else "purchasing_attention"
            if pending_vendor_issues
            else "active"
        )
    db.commit()
    return get_order(db, order.id) or order


def remove_model_for_vendor_attention(
    db: Session,
    order: PurchaseOrder,
    attention_id: str,
    actor: str,
) -> PurchaseOrder:
    if order.status != "purchasing_attention":
        raise OrderLifecycleError("PO is not awaiting Purchasing review")
    attention = next((item for item in order.attention_items if item.id == attention_id), None)
    if (
        attention is None
        or attention.status != "pending"
        or attention.initiated_by_side != "vendor"
        or attention.action_type not in {"backorder", "out_of_stock"}
    ):
        raise OrderLifecycleError("Vendor stock exception was not found")
    line_id = int(attention.payload["line_id"])
    line = next((item for item in order.lines if item.id == line_id), None)
    if line is None:
        raise OrderLifecycleError("PO line was not found")
    quantity_before = line.quantity
    remaining_quantity = line.received_quantity
    remaining_lines = [item for item in order.lines if item.id != line.id]
    if remaining_quantity > 0:
        remaining_lines.append(line)
    if not remaining_lines:
        raise OrderLifecycleError("Removing this model would leave the PO empty")
    quantities = {item.product_code: item.quantity for item in order.lines}
    quantities[line.product_code] = remaining_quantity
    _validate_po_moq(db, order, quantities)
    if remaining_quantity > 0:
        line.quantity = remaining_quantity
    else:
        order.lines.remove(line)
    _recalculate_po(order)

    now = datetime.now(UTC)
    for item in order.attention_items:
        if (
            item.status == "pending"
            and item.initiated_by_side == "vendor"
            and int(item.payload.get("line_id", -1)) == line_id
        ):
            item.status = "acknowledged"
            item.response_note = "Purchasing removed the unreceived model units from the PO."
            item.responded_by = actor
            item.responded_at = now
    _queue_vendor_change_confirmation(
        db,
        order,
        attention,
        actor,
        "removed_out_of_stock_model",
        {
            "po_line_changed": True,
            "product_code": line.product_code,
            "product_name": line.product_name,
            "quantity_before": str(quantity_before),
            "quantity_after": str(remaining_quantity),
            "removed_quantity": str(quantity_before - remaining_quantity),
        },
    )
    other_pending = any(
        item.status == "pending" and item.initiated_by_side == "vendor"
        for item in order.attention_items
    )
    order.status = "purchasing_attention" if other_pending else "vendor_attention"
    db.commit()
    return get_order(db, order.id) or order


def receive_po_line(
    db: Session, order: PurchaseOrder, line_id: int, quantity: Decimal, actor: str
) -> PurchaseOrder:
    if order.status != "active":
        raise OrderLifecycleError("Only active POs can receive items")
    line = next((item for item in order.lines if item.id == line_id), None)
    if line is None:
        raise OrderLifecycleError("PO line was not found")
    if line.received_quantity + quantity > line.quantity:
        raise OrderLifecycleError("Received quantity cannot exceed ordered quantity")
    line.received_quantity += quantity
    db.add(
        EventSnapshot(
            event_type="purchase_order.line_received",
            entity_type="purchase_order_line",
            entity_id=str(line.id),
            actor=actor,
            payload={"quantity": str(quantity), "received_total": str(line.received_quantity)},
        )
    )
    db.commit()
    return db.scalar(_order_query().where(PurchaseOrder.id == order.id)) or order


def complete_reconciliation(db: Session, order: PurchaseOrder, actor: str) -> PurchaseOrder:
    if order.status != "awaiting_reconciliation":
        raise OrderLifecycleError("PO is not awaiting reconciliation")
    order.status = "reconciliation_complete"
    db.add(
        EventSnapshot(
            event_type="purchase_order.reconciliation_completed",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload={"po_number": order.po_number},
        )
    )
    db.commit()
    db.refresh(order)
    return order
