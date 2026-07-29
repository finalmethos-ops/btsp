from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.catalog import CatalogVendor
from app.models.identity import User
from app.models.purchase_order import PurchaseOrder
from app.schemas.catalog import CatalogProductResponse
from app.schemas.order_lifecycle import (
    AttentionResponse,
    GlobalETAUpdate,
    LifecycleLineWrite,
    LifecyclePOResponse,
    LifecycleRequestResponse,
    PurchasingPOChange,
    ReceivePOLine,
    RequestDecision,
    VendorOrderRequestBulkCreate,
    VendorOrderRequestCreate,
    VendorOrderRequestDateUpdate,
    VendorPOIssue,
    VendorPOResponse,
)
from app.services.order_lifecycle_service import (
    OrderLifecycleError,
    complete_reconciliation,
    create_purchasing_po_change,
    create_vendor_po_issue,
    create_vendor_request,
    create_vendor_requests,
    decide_request,
    delete_vendor_request,
    get_request,
    list_purchasing_pos,
    list_purchasing_requests,
    list_substitute_options,
    list_vendor_pos,
    list_vendor_requests,
    receive_po_line,
    remove_model_for_vendor_attention,
    remove_request_line,
    respond_to_attention,
    respond_to_po,
    submit_vendor_request,
    update_active_po_eta,
    update_vendor_request_date,
    write_request_line,
)
from app.services.purchase_order_artifact_service import render_pdf
from app.services.purchase_order_service import get_purchase_order, handoff_purchase_order
from app.services.vendor_model_service import require_vendor_code

router = APIRouter(prefix="/order-lifecycle", tags=["order-lifecycle"])


def _vendor(user: User) -> str:
    try:
        return require_vendor_code(user.vendor_code)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _vendor_order(db: Session, order_id: str, vendor_code: str) -> PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order is None or order.vendor_code != vendor_code:
        raise HTTPException(status_code=404, detail="PO not found")
    return order


@router.get("/vendor/requests", response_model=list[LifecycleRequestResponse])
def vendor_requests(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    return list_vendor_requests(db, _vendor(user))


@router.post("/vendor/requests", response_model=LifecycleRequestResponse, status_code=201)
def create_request(
    payload: VendorOrderRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        return create_vendor_request(
            db,
            _vendor(user),
            payload.store_number,
            user.email,
            payload.expected_delivery_date,
        )
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.delete("/vendor/requests/{request_id}", status_code=204)
def delete_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
) -> Response:
    request = get_request(db, request_id)
    if request is None or request.vendor_code != _vendor(user):
        raise HTTPException(status_code=404, detail="Order request not found")
    try:
        delete_vendor_request(db, request)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc
    return Response(status_code=204)


@router.patch(
    "/vendor/requests/{request_id}/expected-delivery",
    response_model=LifecycleRequestResponse,
)
def update_request_date(
    request_id: str,
    payload: VendorOrderRequestDateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    request = get_request(db, request_id)
    if request is None or request.vendor_code != _vendor(user):
        raise HTTPException(status_code=404, detail="Order request not found")
    try:
        return update_vendor_request_date(db, request, payload.expected_delivery_date, user.email)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.post(
    "/vendor/requests/bulk",
    response_model=list[LifecycleRequestResponse],
    status_code=201,
)
def create_requests_bulk(
    payload: VendorOrderRequestBulkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        return create_vendor_requests(
            db,
            _vendor(user),
            payload.store_numbers,
            user.email,
            payload.expected_delivery_date,
            payload.line_items,
        )
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.put("/vendor/requests/{request_id}/lines", response_model=LifecycleRequestResponse)
def add_vendor_line(
    request_id: str,
    payload: LifecycleLineWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    request = get_request(db, request_id)
    if request is None or request.vendor_code != _vendor(user):
        raise HTTPException(status_code=404, detail="Order request not found")
    try:
        return write_request_line(db, request, payload, user.email)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.put(
    "/vendor/requests/{request_id}/lines/{line_id}",
    response_model=LifecycleRequestResponse,
)
def edit_vendor_line(
    request_id: str,
    line_id: int,
    payload: LifecycleLineWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    request = get_request(db, request_id)
    if request is None or request.vendor_code != _vendor(user):
        raise HTTPException(status_code=404, detail="Order request not found")
    try:
        return write_request_line(db, request, payload, user.email, line_id)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.delete(
    "/vendor/requests/{request_id}/lines/{line_id}",
    response_model=LifecycleRequestResponse,
)
def delete_vendor_line(
    request_id: str,
    line_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    request = get_request(db, request_id)
    if request is None or request.vendor_code != _vendor(user):
        raise HTTPException(status_code=404, detail="Order request not found")
    try:
        return remove_request_line(db, request, line_id, user.email)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.post("/vendor/requests/{request_id}/submit", response_model=LifecycleRequestResponse)
def submit_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    request = get_request(db, request_id)
    if request is None or request.vendor_code != _vendor(user):
        raise HTTPException(status_code=404, detail="Order request not found")
    try:
        return submit_vendor_request(db, request, user.email)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.get("/purchasing/requests", response_model=list[LifecycleRequestResponse])
def purchasing_requests(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("purchase_orders.handoff")),
):
    return list_purchasing_requests(db)


@router.put(
    "/purchasing/requests/{request_id}/lines/{line_id}",
    response_model=LifecycleRequestResponse,
)
def edit_purchasing_line(
    request_id: str,
    line_id: int,
    payload: LifecycleLineWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase_orders.handoff")),
):
    request = get_request(db, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Order request not found")
    try:
        return write_request_line(db, request, payload, user.email, line_id)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.put("/purchasing/requests/{request_id}/lines", response_model=LifecycleRequestResponse)
def add_purchasing_line(
    request_id: str,
    payload: LifecycleLineWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase_orders.handoff")),
):
    request = get_request(db, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Order request not found")
    try:
        return write_request_line(db, request, payload, user.email)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.delete(
    "/purchasing/requests/{request_id}/lines/{line_id}",
    response_model=LifecycleRequestResponse,
)
def delete_purchasing_line(
    request_id: str,
    line_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase_orders.handoff")),
):
    request = get_request(db, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Order request not found")
    try:
        return remove_request_line(db, request, line_id, user.email)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.post("/purchasing/requests/{request_id}/decision")
def purchasing_decision(
    request_id: str,
    payload: RequestDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase_orders.handoff")),
):
    request = get_request(db, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Order request not found")
    try:
        order = decide_request(
            db,
            request,
            payload.action,
            payload.reason,
            user.email,
            payload.expected_delivery_date,
        )
    except OrderLifecycleError as exc:
        raise _error(exc) from exc
    return {"status": request.status, "purchase_order_id": order.id if order else None}


@router.get("/vendor/pos", response_model=list[LifecyclePOResponse])
def vendor_pos(
    queue: str = "pending",
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    entity_code: str | None = None,
    region_code: str | None = None,
    store_number: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    return list_vendor_pos(
        db,
        _vendor(user),
        queue,
        search=search,
        date_from=date_from,
        date_to=date_to,
        entity_code=entity_code,
        region_code=region_code,
        store_number=store_number,
    )


@router.post("/vendor/pos/{order_id}/respond", response_model=LifecyclePOResponse)
def vendor_respond(
    order_id: str,
    payload: VendorPOResponse,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        return respond_to_po(
            db,
            _vendor_order(db, order_id, _vendor(user)),
            payload.action,
            payload.eta,
            payload.reason,
            user.email,
        )
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.get("/vendor/pos/{order_id}/print")
def print_vendor_po(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    order = _vendor_order(db, order_id, _vendor(user))
    return Response(
        content=render_pdf(order),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{order.po_number}.pdf"'},
    )


@router.get("/vendor/pos/{order_id}/email-details")
def vendor_po_email_details(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    order = _vendor_order(db, order_id, _vendor(user))
    vendor = db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == order.vendor_code))
    return {
        "recipient": vendor.po_email_recipient if vendor else None,
        "subject": f"Purchase Order {order.po_number}",
        "body": (
            f"Please find Purchase Order {order.po_number}. "
            f"Total: {order.currency} {order.total}."
        ),
    }


@router.get("/purchasing/pos", response_model=list[LifecyclePOResponse])
def purchasing_pos(
    queue: str = "active",
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    entity_code: str | None = None,
    region_code: str | None = None,
    store_number: str | None = None,
    vendor_code: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("purchase_orders.handoff")),
):
    return list_purchasing_pos(
        db,
        queue,
        search=search,
        date_from=date_from,
        date_to=date_to,
        entity_code=entity_code,
        region_code=region_code,
        store_number=store_number,
        vendor_code=vendor_code,
    )


@router.patch("/vendor/pos/{order_id}/eta", response_model=LifecyclePOResponse)
def vendor_update_eta(
    order_id: str,
    payload: GlobalETAUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        return update_active_po_eta(
            db, _vendor_order(db, order_id, _vendor(user)), payload.eta, user.email
        )
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.post("/vendor/pos/{order_id}/issues", response_model=LifecyclePOResponse)
def vendor_report_issue(
    order_id: str,
    payload: VendorPOIssue,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        return create_vendor_po_issue(
            db,
            _vendor_order(db, order_id, _vendor(user)),
            payload.action,
            payload.line_id,
            payload.quantity,
            payload.eta,
            payload.substitute_product_code,
            payload.reason,
            user.email,
        )
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.get(
    "/vendor/pos/{order_id}/lines/{line_id}/substitute-options",
    response_model=list[CatalogProductResponse],
)
def vendor_substitute_options(
    order_id: str,
    line_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        return list_substitute_options(db, _vendor_order(db, order_id, _vendor(user)), line_id)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.post("/purchasing/pos/{order_id}/changes", response_model=LifecyclePOResponse)
def purchasing_request_change(
    order_id: str,
    payload: PurchasingPOChange,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase_orders.handoff")),
):
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="PO not found")
    try:
        return create_purchasing_po_change(
            db,
            order,
            payload.action,
            user.email,
            payload.reason,
            payload.line_id,
            payload.product_code,
            payload.quantity,
            payload.requested_date,
        )
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.post(
    "/vendor/pos/{order_id}/attention/{attention_id}/respond",
    response_model=LifecyclePOResponse,
)
def vendor_respond_attention(
    order_id: str,
    attention_id: str,
    payload: AttentionResponse,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        return respond_to_attention(
            db,
            _vendor_order(db, order_id, _vendor(user)),
            attention_id,
            payload.action,
            "vendor",
            user.email,
            payload.eta,
            payload.note,
        )
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.post(
    "/purchasing/pos/{order_id}/attention/{attention_id}/acknowledge",
    response_model=LifecyclePOResponse,
)
def purchasing_acknowledge_attention(
    order_id: str,
    attention_id: str,
    payload: AttentionResponse,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase_orders.handoff")),
):
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="PO not found")
    try:
        return respond_to_attention(
            db,
            order,
            attention_id,
            "acknowledge",
            "purchasing",
            user.email,
            note=payload.note,
        )
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.post(
    "/purchasing/pos/{order_id}/attention/{attention_id}/remove-model",
    response_model=LifecyclePOResponse,
)
def purchasing_remove_attention_model(
    order_id: str,
    attention_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase_orders.handoff")),
):
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="PO not found")
    try:
        return remove_model_for_vendor_attention(db, order, attention_id, user.email)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.post(
    "/purchasing/pos/{order_id}/lines/{line_id}/receive",
    response_model=LifecyclePOResponse,
)
def receive_line(
    order_id: str,
    line_id: int,
    payload: ReceivePOLine,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase_orders.handoff")),
):
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="PO not found")
    if order.status != "active":
        raise HTTPException(status_code=409, detail="Only active POs can receive items")
    try:
        return receive_po_line(db, order, line_id, payload.quantity, user.email)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc


@router.post("/purchasing/pos/{order_id}/handoff", response_model=LifecyclePOResponse)
def lifecycle_handoff(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase_orders.handoff")),
):
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="PO not found")
    if order.status != "active":
        raise HTTPException(status_code=409, detail="Only active POs can be handed off")
    try:
        return handoff_purchase_order(db, order, user.email)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/reconciliation/pos/{order_id}/complete", response_model=LifecyclePOResponse)
def reconcile_complete(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reconciliation.manage")),
):
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="PO not found")
    try:
        return complete_reconciliation(db, order, user.email)
    except OrderLifecycleError as exc:
        raise _error(exc) from exc
