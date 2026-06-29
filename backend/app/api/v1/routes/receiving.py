from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.permissions import get_permission_codes, require_permission
from app.db.session import get_db
from app.models.identity import User
from app.models.receiving import ReceiptVariance
from app.schemas.receiving import (
    PurchaseBackorderAction,
    PurchaseBackorderCreate,
    PurchaseBackorderResponse,
    PurchaseReceiptCreate,
    PurchaseReceiptResponse,
    ReceiptVarianceResolution,
    ReceiptVarianceResponse,
)
from app.services.backorder_service import (
    BackorderError,
    apply_backorder_action,
    create_backorder,
    list_backorders,
)
from app.services.receipt_variance_service import (
    ReceiptVarianceError,
    list_receipt_variances,
    resolve_receipt_variance,
)
from app.services.receiving_service import (
    ReceivingError,
    create_receipt,
    get_receipt,
    list_receipts,
)

router = APIRouter(prefix="/receipts", tags=["receiving"])


def _store_scope(user: User, requested_store: str | None) -> str | None:
    if "system.admin" in get_permission_codes(user):
        return requested_store
    if user.home_store_number is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Receiving access requires an assigned home store",
        )
    if requested_store is not None and requested_store != user.home_store_number:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Store access denied")
    return user.home_store_number


@router.post("", response_model=PurchaseReceiptResponse)
def post_receipt(
    payload: PurchaseReceiptCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.manage")),
) -> PurchaseReceiptResponse:
    _store_scope(user, payload.store_number)
    try:
        receipt, created = create_receipt(db, payload, user.email)
    except ReceivingError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return PurchaseReceiptResponse.model_validate(receipt)


@router.get("", response_model=list[PurchaseReceiptResponse])
def read_receipts(
    purchase_order_id: str | None = None,
    store_number: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.read")),
) -> list[PurchaseReceiptResponse]:
    scoped_store = _store_scope(user, store_number)
    return [
        PurchaseReceiptResponse.model_validate(receipt)
        for receipt in list_receipts(db, purchase_order_id, scoped_store)
    ]


@router.get("/{receipt_id}", response_model=PurchaseReceiptResponse)
def read_receipt(
    receipt_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.read")),
) -> PurchaseReceiptResponse:
    receipt = get_receipt(db, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    _store_scope(user, receipt.store_number)
    return PurchaseReceiptResponse.model_validate(receipt)


@router.get("/variances/open", response_model=list[ReceiptVarianceResponse])
def read_variances(
    variance_status: str | None = "open",
    store_number: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.read")),
) -> list[ReceiptVarianceResponse]:
    scoped_store = _store_scope(user, store_number)
    return [
        ReceiptVarianceResponse.model_validate(item)
        for item in list_receipt_variances(db, variance_status, scoped_store)
    ]


@router.post(
    "/variances/{variance_id}/resolution",
    response_model=ReceiptVarianceResponse,
)
def resolve_variance(
    variance_id: str,
    payload: ReceiptVarianceResolution,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.variances.manage")),
) -> ReceiptVarianceResponse:
    variance = db.get(ReceiptVariance, variance_id)
    if variance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variance not found")
    receipt = get_receipt(db, variance.receipt_id)
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    _store_scope(user, receipt.store_number)
    try:
        resolved = resolve_receipt_variance(db, variance_id, payload, user.email)
    except ReceiptVarianceError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReceiptVarianceResponse.model_validate(resolved)


@router.post("/backorders/create", response_model=PurchaseBackorderResponse)
def post_backorder(
    payload: PurchaseBackorderCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.backorders.manage")),
) -> PurchaseBackorderResponse:
    variance = db.get(ReceiptVariance, payload.source_variance_id)
    if variance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variance not found")
    receipt = get_receipt(db, variance.receipt_id)
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
    _store_scope(user, receipt.store_number)
    try:
        backorder, created = create_backorder(db, payload, user.email)
    except BackorderError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return PurchaseBackorderResponse.model_validate(backorder)


@router.get("/backorders/list", response_model=list[PurchaseBackorderResponse])
def read_backorders(
    backorder_status: str | None = None,
    store_number: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.read")),
) -> list[PurchaseBackorderResponse]:
    scoped_store = _store_scope(user, store_number)
    return [
        PurchaseBackorderResponse.model_validate(item)
        for item in list_backorders(db, backorder_status, scoped_store)
    ]


@router.post(
    "/backorders/{backorder_id}/actions",
    response_model=PurchaseBackorderResponse,
)
def run_backorder_action(
    backorder_id: str,
    payload: PurchaseBackorderAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("receiving.backorders.manage")),
) -> PurchaseBackorderResponse:
    backorder = next(
        (item for item in list_backorders(db) if item.id == backorder_id),
        None,
    )
    if backorder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backorder not found")
    _store_scope(user, backorder.store_number)
    try:
        updated = apply_backorder_action(db, backorder_id, payload, user.email)
    except BackorderError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return PurchaseBackorderResponse.model_validate(updated)
