import csv
import re
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import CatalogProduct
from app.models.event_management import (
    EventEntityOrder,
    EventEntityOrderRevision,
    EventOrderReleaseBatch,
    EventOrderReleaseLine,
    EventOrderReviewEvent,
    EventProductSlide,
    ManagedEvent,
    ManagedSubEvent,
)
from app.models.identity import User
from app.models.purchasing import PurchaseRequest, PurchaseRequestLineItem
from app.models.store import Store
from app.schemas.event_order_review import (
    EventOrderPurchasingLink,
    EventOrderReleaseResponse,
    EventOrderReviewDecision,
    EventOrderReviewItem,
    EventOrderReviewSummary,
    EventOrderVariantLine,
)
from app.services.event_access_service import event_operations_are_locked
from app.services.spreadsheet_security import spreadsheet_safe_row


class EventOrderReviewError(ValueError):
    pass


def _variant_release_lines(order: EventEntityOrder, slide: EventProductSlide):
    variants = {str(item["model_number"]): item for item in (slide.product_variants or [])}
    if variants and order.variant_quantities:
        return [
            (
                model,
                quantity,
                Decimal(str(variants[model]["event_unit_cost"])),
                Decimal(str(variants[model]["event_unit_cost"])) * quantity,
            )
            for model, quantity in order.variant_quantities.items()
            if quantity > 0 and model in variants
        ]
    return [(slide.model_number, order.quantity, order.unit_cost, order.total_cost)]


def _scale_variant_quantities(values: dict[str, int], target: int) -> dict[str, int]:
    current = sum(values.values())
    if not current or current == target:
        return values
    raw = {model: quantity * target / current for model, quantity in values.items()}
    scaled = {model: int(value) for model, value in raw.items()}
    remainder = target - sum(scaled.values())
    for model in sorted(raw, key=lambda item: raw[item] - scaled[item], reverse=True)[:remainder]:
        scaled[model] += 1
    return {model: quantity for model, quantity in scaled.items() if quantity > 0}


def _release_store(db: Session, order: EventEntityOrder) -> str:
    stores = list(
        db.scalars(
            select(Store).where(
                Store.entity_code == order.entity_code,
                Store.is_active.is_(True),
                Store.is_ordering_enabled.is_(True),
            )
        ).all()
    )
    user = db.get(User, order.user_id)
    if (
        user
        and user.home_store_number
        and any(store.store_number == user.home_store_number for store in stores)
    ):
        return user.home_store_number
    if len(stores) == 1:
        return stores[0].store_number
    if not stores:
        raise EventOrderReviewError(
            f"No active ordering store is configured for entity {order.entity_code}"
        )
    raise EventOrderReviewError(
        f"Entity {order.entity_code} has multiple stores; assign a home store to its event account"
    )


def _release_product(
    db: Session,
    event: ManagedEvent,
    slide: EventProductSlide,
    model_number: str,
    product_name: str,
    unit_cost: Decimal,
) -> CatalogProduct:
    product = db.scalar(
        select(CatalogProduct).where(
            CatalogProduct.model_number == model_number,
        )
    )
    if product:
        if product.vendor_code != slide.vendor_code:
            raise EventOrderReviewError(
                f"Model {model_number} already belongs to vendor {product.vendor_code}"
            )
        return product
    stem = re.sub(r"[^A-Z0-9]+", "-", model_number.upper()).strip("-") or "MODEL"
    base = f"EVT-{stem}"[:58]
    product_code = base
    sequence = 2
    while db.scalar(select(CatalogProduct.id).where(CatalogProduct.product_code == product_code)):
        suffix = f"-{sequence}"
        product_code = f"{base[:64-len(suffix)]}{suffix}"
        sequence += 1
    product = CatalogProduct(
        product_code=product_code,
        model_number=model_number,
        vendor_code=slide.vendor_code,
        name=product_name,
        unit_price=unit_cost,
        currency=slide.currency,
        minimum_order_quantity=1,
        is_available=True,
        is_active=True,
        source_file=f"event-release:{event.id}",
    )
    db.add(product)
    db.flush()
    return product


def _rows(db: Session, event_id: str):
    return db.execute(
        select(EventEntityOrder, EventProductSlide, ManagedSubEvent)
        .join(EventProductSlide, EventProductSlide.id == EventEntityOrder.slide_id)
        .join(ManagedSubEvent, ManagedSubEvent.id == EventEntityOrder.sub_event_id)
        .where(EventEntityOrder.event_id == event_id)
        .order_by(
            ManagedSubEvent.starts_at, EventProductSlide.position, EventEntityOrder.entity_code
        )
    ).all()


def review_summary(db: Session, event_id: str) -> EventOrderReviewSummary | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    rows = _rows(db, event_id)
    purchasing_links: dict[str, dict[str, PurchaseRequest]] = {}
    for release_line, request in db.execute(
        select(EventOrderReleaseLine, PurchaseRequest)
        .join(PurchaseRequest, PurchaseRequest.id == EventOrderReleaseLine.purchase_request_id)
        .join(EventOrderReleaseBatch, EventOrderReleaseBatch.id == EventOrderReleaseLine.batch_id)
        .where(EventOrderReleaseBatch.event_id == event_id)
    ).all():
        purchasing_links.setdefault(release_line.order_id, {})[request.id] = request
    items = [
        EventOrderReviewItem(
            order_id=order.id,
            sub_event_name=sub_event.name,
            entity_code=order.entity_code,
            vendor_code=slide.vendor_code,
            model_number=slide.model_number,
            product_name=slide.name,
            quantity=order.quantity,
            unit_cost=order.unit_cost,
            total_cost=order.total_cost,
            requested_delivery_start=order.requested_delivery_start,
            requested_delivery_end=order.requested_delivery_end,
            live_status=order.status,
            review_status=order.review_status,
            reviewed_by=order.reviewed_by,
            reviewed_at=order.reviewed_at,
            variant_lines=[
                EventOrderVariantLine(
                    model_number=model_number,
                    product_name=next(
                        (
                            str(item["name"])
                            for item in (slide.product_variants or [])
                            if str(item["model_number"]) == model_number
                        ),
                        slide.name,
                    ),
                    quantity=quantity,
                    unit_cost=unit_cost,
                    total_cost=total_cost,
                )
                for model_number, quantity, unit_cost, total_cost in _variant_release_lines(
                    order, slide
                )
            ],
            purchasing_requests=[
                EventOrderPurchasingLink(
                    purchase_request_id=request.id,
                    order_number=request.order_number,
                    status=request.status,
                )
                for request in purchasing_links.get(order.id, {}).values()
            ],
        )
        for order, slide, sub_event in rows
    ]
    approved = [item for item in items if item.review_status == "approved"]
    return EventOrderReviewSummary(
        event_id=event.id,
        event_name=event.name,
        pending=sum(item.review_status == "pending" for item in items),
        approved=len(approved),
        rejected=sum(item.review_status == "rejected" for item in items),
        released=sum(item.review_status == "released" for item in items),
        approved_units=sum(item.quantity for item in approved),
        approved_spend=sum((item.total_cost for item in approved), Decimal("0")),
        items=items,
    )


def decide_order(
    db: Session,
    order_id: str,
    payload: EventOrderReviewDecision,
    actor: str,
) -> str | None:
    order = db.scalar(
        select(EventEntityOrder).where(EventEntityOrder.id == order_id).with_for_update()
    )
    if order is None:
        return None
    if event_operations_are_locked(db, order.event_id):
        raise EventOrderReviewError(
            "Event order review is locked because the event is cancelled or settlement is closed"
        )
    if order.review_status == "released":
        raise EventOrderReviewError("Released orders cannot be changed")
    slide = db.get(EventProductSlide, order.slide_id)
    previous_quantity = order.quantity
    resulting_quantity = payload.revised_quantity or order.quantity
    if resulting_quantity < slide.minimum_order_quantity:
        raise EventOrderReviewError(
            f"Quantity must meet the minimum order quantity of {slide.minimum_order_quantity}"
        )
    if payload.decision == "revise":
        order.quantity = resulting_quantity
        if order.variant_quantities and slide.product_variants:
            order.variant_quantities = _scale_variant_quantities(
                order.variant_quantities, resulting_quantity
            )
            variants = {str(item["model_number"]): item for item in slide.product_variants}
            order.total_cost = sum(
                Decimal(str(variants[model]["event_unit_cost"])) * quantity
                for model, quantity in order.variant_quantities.items()
            )
            order.unit_cost = order.total_cost / resulting_quantity
        else:
            order.total_cost = Decimal(resulting_quantity) * order.unit_cost
    order.review_status = "rejected" if payload.decision == "reject" else "approved"
    order.reviewed_by = actor
    order.reviewed_at = datetime.now(UTC)
    db.add(
        EventOrderReviewEvent(
            order_id=order.id,
            decision=payload.decision,
            previous_quantity=previous_quantity,
            resulting_quantity=order.quantity,
            reason=(payload.reason or "").strip() or None,
            actor=actor,
        )
    )
    revision = (
        db.scalar(
            select(func.count(EventEntityOrderRevision.id)).where(
                EventEntityOrderRevision.order_id == order.id
            )
        )
        or 0
    )
    db.add(
        EventEntityOrderRevision(
            order_id=order.id,
            revision=revision + 1,
            quantity=order.quantity,
            requested_delivery_start=order.requested_delivery_start,
            requested_delivery_end=order.requested_delivery_end,
            status=f"review_{order.review_status}",
            changed_by=actor,
        )
    )
    db.commit()
    return order.event_id


def release_approved_orders(
    db: Session, event_id: str, actor: str
) -> EventOrderReleaseResponse | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    if event_operations_are_locked(db, event_id):
        raise EventOrderReviewError(
            "Event order release is locked because the event is cancelled or settlement is closed"
        )
    rows = db.execute(
        select(EventEntityOrder, EventProductSlide)
        .join(EventProductSlide, EventProductSlide.id == EventEntityOrder.slide_id)
        .where(
            EventEntityOrder.event_id == event_id,
            EventEntityOrder.review_status == "approved",
        )
        .with_for_update()
    ).all()
    if not rows:
        raise EventOrderReviewError("No approved, unreleased event orders are available")
    batch = EventOrderReleaseBatch(event_id=event_id, status="staged", created_by=actor)
    db.add(batch)
    db.flush()
    grouped_requests: dict[tuple[str, str], PurchaseRequest] = {}
    release_pairs: list[tuple[EventOrderReleaseLine, PurchaseRequest]] = []
    vendor_sequences: dict[str, int] = {}
    existing_event_requests = db.scalars(
        select(PurchaseRequest).where(PurchaseRequest.workflow_code == "VENDOR_ORDER")
    ).all()
    for request in existing_event_requests:
        if request.context.get("event_id") == event.id:
            vendor_sequences[request.vendor_code] = max(
                vendor_sequences.get(request.vendor_code, 0),
                int(request.context.get("event_order_sequence", 0)),
            )
    for order, slide in rows:
        store_number = _release_store(db, order)
        key = (store_number, slide.vendor_code)
        request = grouped_requests.get(key)
        if request is None:
            vendor_sequences[slide.vendor_code] = vendor_sequences.get(slide.vendor_code, 0) + 1
            request = PurchaseRequest(
                order_number=f"{event.name}-{store_number}-{slide.vendor_code}-{vendor_sequences[slide.vendor_code]:03d}",
                workflow_code="VENDOR_ORDER",
                store_number=store_number,
                vendor_code=slide.vendor_code,
                status="submitted_to_purchasing",
                context={
                    "source": "event_live_order_release",
                    "event_id": event.id,
                    "event_name": event.name,
                    "release_batch_id": batch.id,
                    "entity_code": order.entity_code,
                    "event_order_sequence": vendor_sequences[slide.vendor_code],
                    "event_order_ids": [order.id],
                },
                created_by=actor,
                updated_by=actor,
            )
            grouped_requests[key] = request
            db.add(request)
        elif order.id not in request.context.get("event_order_ids", []):
            request.context = {
                **request.context,
                "event_order_ids": [*request.context.get("event_order_ids", []), order.id],
            }
        variants = {str(item["model_number"]): item for item in (slide.product_variants or [])}
        for model_number, quantity, unit_cost, total_cost in _variant_release_lines(order, slide):
            product_name = str(variants.get(model_number, {}).get("name", slide.name))
            product = _release_product(db, event, slide, model_number, product_name, unit_cost)
            request.line_items.append(
                PurchaseRequestLineItem(
                    product_code=product.product_code,
                    product_name=product_name,
                    quantity=quantity,
                    unit_price=unit_cost,
                    freight_amount=Decimal("0"),
                    tax_amount=Decimal("0"),
                    extended_amount=total_cost,
                    notes=f"Event order {order.id}; release batch {batch.id}",
                    requested_delivery_date=order.requested_delivery_start,
                )
            )
            release_line = EventOrderReleaseLine(
                batch_id=batch.id,
                order_id=order.id,
                vendor_code=slide.vendor_code,
                entity_code=order.entity_code,
                model_number=model_number,
                quantity=quantity,
                unit_cost=unit_cost,
                total_cost=total_cost,
                requested_delivery_start=order.requested_delivery_start,
                requested_delivery_end=order.requested_delivery_end,
            )
            db.add(release_line)
            release_pairs.append((release_line, request))
        order.review_status = "released"
        order.reviewed_by = actor
        order.reviewed_at = datetime.now(UTC)
    for request in grouped_requests.values():
        request.subtotal = sum((line.extended_amount for line in request.line_items), Decimal("0"))
        request.total = request.subtotal
        request.expected_delivery_date = min(
            line.requested_delivery_date
            for line in request.line_items
            if line.requested_delivery_date is not None
        )
    db.flush()
    for release_line, request in release_pairs:
        release_line.purchase_request_id = request.id
    db.commit()
    db.refresh(batch)
    return EventOrderReleaseResponse(
        batch_id=batch.id,
        event_id=event_id,
        order_count=len(rows),
        vendor_count=len({slide.vendor_code for _, slide in rows}),
        entity_count=len({order.entity_code for order, _ in rows}),
        total_units=sum(order.quantity for order, _ in rows),
        total_spend=sum((order.total_cost for order, _ in rows), Decimal("0")),
        purchase_request_count=len(grouped_requests),
        status=batch.status,
        created_at=batch.created_at,
    )


def export_review_csv(db: Session, event_id: str) -> str | None:
    summary = review_summary(db, event_id)
    if summary is None:
        return None
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        spreadsheet_safe_row(
            [
                "sub_event",
                "entity_code",
                "vendor_code",
                "model_number",
                "product_name",
                "quantity",
                "unit_cost",
                "total_cost",
                "delivery_start",
                "delivery_end",
                "live_status",
                "review_status",
            ]
        )
    )
    for item in summary.items:
        lines = item.variant_lines if len(item.variant_lines) > 1 else [item]
        for line in lines:
            writer.writerow(
                spreadsheet_safe_row(
                    [
                        item.sub_event_name,
                        item.entity_code,
                        item.vendor_code,
                        line.model_number,
                        line.product_name,
                        line.quantity,
                        line.unit_cost,
                        line.total_cost,
                        item.requested_delivery_start,
                        item.requested_delivery_end,
                        item.live_status,
                        item.review_status,
                    ]
                )
            )
    return output.getvalue()
