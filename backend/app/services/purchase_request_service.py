from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attachment import PurchaseRequestAttachment
from app.models.catalog import CatalogProduct, CatalogVendor
from app.models.identity import User
from app.models.purchasing import PurchaseRequest, PurchaseRequestLineItem
from app.models.store import Store
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.flow import FlowStartRequest
from app.schemas.purchasing import PurchaseLineWrite, PurchaseRequestCreate, PurchaseRequestUpdate
from app.services.configuration_service import get_config_entry
from app.services.purchasing_rule_service import (
    RuleEvaluation,
    RuleIssue,
    evaluate_purchase_request,
    load_purchasing_rules,
)
from app.services.snapshot_service import append_snapshot
from app.services.store_service import check_region_scope
from app.services.workflow_engine import WorkflowError, get_active_definition, start_workflow

SUPPORTED_WORKFLOWS = {"BPP_PURCHASING", "IND_PURCHASING"}


class PurchaseRequestError(ValueError):
    pass


def _validate_references(db: Session, store_number: str, vendor_code: str) -> None:
    store = db.scalar(select(Store).where(Store.store_number == store_number))
    if store is None or not store.is_active or not store.is_ordering_enabled:
        raise PurchaseRequestError("Store is not active or enabled for ordering")
    vendor = db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == vendor_code))
    if vendor is None or not vendor.is_active:
        raise PurchaseRequestError("Vendor is not active in the internal catalog")


def _ensure_draft(request: PurchaseRequest) -> None:
    if request.status != "draft":
        raise PurchaseRequestError("Only draft purchase requests can be changed")


def _is_past(value: datetime) -> bool:
    now = datetime.now(UTC)
    if value.tzinfo is None:
        now = now.replace(tzinfo=None)
    return value <= now


def _recalculate(request: PurchaseRequest) -> None:
    request.subtotal = sum(
        (line.quantity * line.unit_price for line in request.line_items), Decimal("0")
    )
    request.freight_total = sum((line.freight_amount for line in request.line_items), Decimal("0"))
    request.tax_total = sum((line.tax_amount for line in request.line_items), Decimal("0"))
    request.total = request.subtotal + request.freight_total + request.tax_total


def create_purchase_request(
    db: Session, payload: PurchaseRequestCreate, actor: str
) -> PurchaseRequest:
    if payload.workflow_code not in SUPPORTED_WORKFLOWS:
        raise PurchaseRequestError("Unsupported purchasing workflow")
    _validate_references(db, payload.store_number, payload.vendor_code)
    rules = load_purchasing_rules(db, payload.workflow_code)
    days = rules.get("draft.expiration_days", {}).get("days", 30)
    if not isinstance(days, int) or days < 1:
        raise PurchaseRequestError("Draft expiration configuration is invalid")
    request = PurchaseRequest(
        **payload.model_dump(),
        created_by=actor,
        updated_by=actor,
        expires_at=datetime.now(UTC) + timedelta(days=days),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="purchase_request.created",
            entity_type="purchase_request",
            entity_id=request.id,
            actor=actor,
            payload={
                "workflow_code": request.workflow_code,
                "store_number": request.store_number,
                "vendor_code": request.vendor_code,
            },
        ),
    )
    return request


def update_purchase_request(
    db: Session, request: PurchaseRequest, payload: PurchaseRequestUpdate, actor: str
) -> PurchaseRequest:
    _ensure_draft(request)
    values = payload.model_dump(exclude_unset=True)
    expected_revision = values.pop("expected_revision", None)
    if expected_revision is not None and expected_revision != request.revision:
        raise PurchaseRequestError("Draft was changed by another operation; reload and retry")
    store_number = values.get("store_number", request.store_number)
    vendor_code = values.get("vendor_code", request.vendor_code)
    _validate_references(db, store_number, vendor_code)
    if vendor_code != request.vendor_code and request.line_items:
        raise PurchaseRequestError("Remove line items before changing the vendor")
    for key, value in values.items():
        setattr(request, key, value)
    request.updated_by = actor
    request.revision += 1
    db.commit()
    db.refresh(request)
    return request


def add_line_item(
    db: Session, request: PurchaseRequest, payload: PurchaseLineWrite, actor: str
) -> PurchaseRequestLineItem:
    _ensure_draft(request)
    product = db.scalar(
        select(CatalogProduct).where(CatalogProduct.product_code == payload.product_code)
    )
    if product is None or not product.is_active or not product.is_available:
        raise PurchaseRequestError("Product is not active and available in the internal catalog")
    if product.vendor_code != request.vendor_code:
        raise PurchaseRequestError("Product does not belong to the request vendor")
    if payload.quantity < product.minimum_order_quantity:
        raise PurchaseRequestError(f"Quantity must be at least {product.minimum_order_quantity}")
    line = PurchaseRequestLineItem(
        purchase_request=request,
        product_code=product.product_code,
        product_name=product.name,
        quantity=payload.quantity,
        unit_price=product.unit_price,
        freight_amount=payload.freight_amount,
        tax_amount=payload.tax_amount,
        extended_amount=(payload.quantity * product.unit_price)
        + payload.freight_amount
        + payload.tax_amount,
        notes=payload.notes,
    )
    db.add(line)
    db.flush()
    _recalculate(request)
    request.updated_by = actor
    request.revision += 1
    db.commit()
    db.refresh(line)
    return line


def update_line_item(
    db: Session,
    request: PurchaseRequest,
    line: PurchaseRequestLineItem,
    payload: PurchaseLineWrite,
    actor: str,
) -> PurchaseRequestLineItem:
    _ensure_draft(request)
    product = db.scalar(
        select(CatalogProduct).where(CatalogProduct.product_code == payload.product_code)
    )
    if product is None or not product.is_active or not product.is_available:
        raise PurchaseRequestError("Product is not active and available in the internal catalog")
    if product.vendor_code != request.vendor_code:
        raise PurchaseRequestError("Product does not belong to the request vendor")
    if payload.quantity < product.minimum_order_quantity:
        raise PurchaseRequestError(f"Quantity must be at least {product.minimum_order_quantity}")
    line.product_code = product.product_code
    line.product_name = product.name
    line.quantity = payload.quantity
    line.unit_price = product.unit_price
    line.freight_amount = payload.freight_amount
    line.tax_amount = payload.tax_amount
    line.extended_amount = (
        payload.quantity * product.unit_price + payload.freight_amount + payload.tax_amount
    )
    line.notes = payload.notes
    _recalculate(request)
    request.updated_by = actor
    request.revision += 1
    db.commit()
    db.refresh(line)
    return line


def delete_line_item(
    db: Session, request: PurchaseRequest, line: PurchaseRequestLineItem, actor: str
) -> None:
    _ensure_draft(request)
    request.line_items.remove(line)
    db.flush()
    _recalculate(request)
    request.updated_by = actor
    request.revision += 1
    db.commit()


def validate_purchase_request(db: Session, request: PurchaseRequest) -> RuleEvaluation:
    result = RuleEvaluation()
    if request.status != "draft":
        result.errors.append(
            RuleIssue("status.invalid", "Request is not an active draft", "status")
        )
    if request.expires_at is not None and _is_past(request.expires_at):
        result.errors.append(RuleIssue("draft.expired", "Draft has expired", "expires_at"))
    store = db.scalar(select(Store).where(Store.store_number == request.store_number))
    if store is None or not store.is_active or not store.is_ordering_enabled:
        result.errors.append(
            RuleIssue("store.invalid", "Store is not active or orderable", "store_number")
        )
        return result
    vendor = db.scalar(
        select(CatalogVendor).where(CatalogVendor.vendor_code == request.vendor_code)
    )
    if vendor is None or not vendor.is_active:
        result.errors.append(RuleIssue("vendor.invalid", "Vendor is not active", "vendor_code"))
    for line in request.line_items:
        product = line.catalog_product
        if product is None or not product.is_active or not product.is_available:
            result.errors.append(
                RuleIssue(
                    "product.invalid", f"Product {line.product_code} is unavailable", "line_items"
                )
            )
        elif line.quantity < product.minimum_order_quantity:
            result.errors.append(
                RuleIssue(
                    "quantity.minimum",
                    f"Product {line.product_code} requires quantity "
                    f"{product.minimum_order_quantity}",
                    "line_items",
                )
            )
    configured = evaluate_purchase_request(
        request,
        store_region=store.region_code,
        buying_group=store.buying_group_code,
        config=load_purchasing_rules(db, request.workflow_code),
    )
    result.errors.extend(configured.errors)
    result.warnings.extend(configured.warnings)
    rules = load_purchasing_rules(db, request.workflow_code)
    required_categories = rules.get("rules.required_attachment_categories", {}).get(
        "categories", []
    )
    if isinstance(required_categories, list):
        present_categories = set(
            db.scalars(
                select(PurchaseRequestAttachment.category).where(
                    PurchaseRequestAttachment.purchase_request_id == request.id,
                    PurchaseRequestAttachment.is_deleted.is_(False),
                )
            ).all()
        )
        for category in required_categories:
            if category not in present_categories:
                result.errors.append(
                    RuleIssue(
                        "attachment.required",
                        f"Attachment category {category} is required",
                        "attachments",
                    )
                )
    workflow_config = get_config_entry(db, "workflow", request.workflow_code, "enabled")
    if workflow_config is not None and workflow_config.value.get("enabled") is not True:
        result.errors.append(
            RuleIssue("workflow.disabled", "Purchasing workflow is disabled", "workflow_code")
        )
    try:
        get_active_definition(db, request.workflow_code)
    except WorkflowError:
        result.errors.append(
            RuleIssue(
                "workflow.unavailable",
                "Active purchasing workflow definition is unavailable",
                "workflow_code",
            )
        )
    return result


def clone_purchase_request(db: Session, source: PurchaseRequest, actor: str) -> PurchaseRequest:
    clone = create_purchase_request(
        db,
        PurchaseRequestCreate(
            workflow_code=source.workflow_code,
            store_number=source.store_number,
            vendor_code=source.vendor_code,
            context=dict(source.context),
        ),
        actor,
    )
    clone.cloned_from_id = source.id
    for source_line in source.line_items:
        add_line_item(
            db,
            clone,
            PurchaseLineWrite(
                product_code=source_line.product_code,
                quantity=source_line.quantity,
                freight_amount=source_line.freight_amount,
                tax_amount=source_line.tax_amount,
                notes=source_line.notes,
            ),
            actor,
        )
    db.commit()
    db.refresh(clone)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="purchase_request.cloned",
            entity_type="purchase_request",
            entity_id=clone.id,
            actor=actor,
            payload={"source_purchase_request_id": source.id},
        ),
    )
    return clone


def expire_stale_drafts(db: Session, actor: str) -> int:
    now = datetime.now(UTC)
    drafts = list(
        db.scalars(
            select(PurchaseRequest).where(
                PurchaseRequest.status == "draft",
                PurchaseRequest.expires_at.is_not(None),
                PurchaseRequest.expires_at <= now,
            )
        ).all()
    )
    for request in drafts:
        request.status = "expired"
        request.updated_by = actor
        request.revision += 1
    db.commit()
    for request in drafts:
        append_snapshot(
            db,
            EventSnapshotCreate(
                event_type="purchase_request.expired",
                entity_type="purchase_request",
                entity_id=request.id,
                actor=actor,
                payload={"expired_at": now.isoformat()},
            ),
        )
    return len(drafts)


def submit_purchase_request(
    db: Session, request: PurchaseRequest, user: User, permission_codes: set[str]
) -> PurchaseRequest:
    _ensure_draft(request)
    required_permission = (
        "workflow.bpp.submit"
        if request.workflow_code == "BPP_PURCHASING"
        else "workflow.ind.submit"
    )
    if required_permission not in permission_codes:
        raise PermissionError(required_permission)
    if not request.line_items:
        raise PurchaseRequestError("Purchase request must contain at least one line item")
    _validate_references(db, request.store_number, request.vendor_code)
    validation = validate_purchase_request(db, request)
    if not validation.ready:
        raise PurchaseRequestError("; ".join(issue.message for issue in validation.errors))
    if user.region_code is not None and check_region_scope(
        db, user.region_code, [request.store_number]
    ):
        raise PermissionError("store.region")
    if request.workflow_code == "IND_PURCHASING" and user.region_code is None:
        raise PurchaseRequestError("Independent purchasing requires an assigned user region")
    instance = start_workflow(
        db,
        FlowStartRequest(
            workflow_code=request.workflow_code,
            entity_type="purchase_request",
            entity_id=request.id,
            context={
                **request.context,
                "store_number": request.store_number,
                "vendor_code": request.vendor_code,
                "request_amount": float(request.total),
            },
        ),
        actor=user.email,
    )
    request.workflow_instance_id = instance.id
    request.status = "submitted"
    request.updated_by = user.email
    db.commit()
    db.refresh(request)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="purchase_request.submitted",
            entity_type="purchase_request",
            entity_id=request.id,
            actor=user.email,
            payload={"workflow_instance_id": instance.id, "total": str(request.total)},
        ),
    )
    return request
