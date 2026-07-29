from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import get_permission_codes, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.models.identity import User
from app.models.purchase_order import PurchaseOrder
from app.schemas.purchase_order import (
    PurchaseOrderGenerateRequest,
    PurchaseOrderResponse,
    PurchaseOrderSeedResponse,
)
from app.schemas.purchase_order_artifact import (
    PurchaseOrderArtifactFormat,
    PurchaseOrderArtifactResponse,
)
from app.schemas.purchase_order_transmission import (
    PurchaseOrderTransmissionActionRequest,
    PurchaseOrderTransmissionCreate,
    PurchaseOrderTransmissionResponse,
)
from app.services.purchase_order_artifact_service import (
    PurchaseOrderArtifactError,
    artifact_path,
    generate_artifact,
    get_artifact,
    list_artifacts,
)
from app.services.purchase_order_service import (
    PurchaseOrderError,
    generate_purchase_orders,
    get_purchase_order,
    handoff_purchase_order,
    list_purchase_orders,
    list_reconciliation_purchase_orders,
    seed_purchase_order_defaults,
)
from app.services.purchase_order_transmission_service import (
    PurchaseOrderTransmissionError,
    apply_transmission_action,
    create_transmission,
    get_transmission,
    list_transmissions,
)

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


def _allowed_workflows(user: User) -> set[str]:
    permissions = get_permission_codes(user)
    if "system.admin" in permissions:
        return set()
    allowed: set[str] = set()
    if "orders.bpp.manage" in permissions:
        allowed.add("BPP_PURCHASING")
    if "orders.independent.manage" in permissions:
        allowed.add("IND_PURCHASING")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Purchase order access denied",
        )
    return allowed


def _ensure_order_access(user: User, order: PurchaseOrder) -> None:
    allowed = _allowed_workflows(user)
    if allowed and order.workflow_code not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Purchase order access denied",
        )


@router.post("/seed-defaults", response_model=PurchaseOrderSeedResponse)
def seed_defaults(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("configuration.manage")),
) -> PurchaseOrderSeedResponse:
    return PurchaseOrderSeedResponse(seeded_count=seed_purchase_order_defaults(db, user.email))


@router.post("/generate", response_model=list[PurchaseOrderResponse])
def generate(
    payload: PurchaseOrderGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PurchaseOrder]:
    _allowed_workflows(user)
    try:
        orders = generate_purchase_orders(
            db, payload.purchase_request_ids, user.email, get_permission_codes(user)
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {exc}",
        ) from exc
    except PurchaseOrderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    for order in orders:
        _ensure_order_access(user, order)
    return orders


@router.get("", response_model=list[PurchaseOrderResponse])
def read_orders(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[PurchaseOrder]:
    return list_purchase_orders(db, _allowed_workflows(user))


@router.get("/reconciliation-queue", response_model=list[PurchaseOrderResponse])
def read_reconciliation_queue(
    queue: str = "active",
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    entity_code: str | None = None,
    region_code: str | None = None,
    store_number: str | None = None,
    vendor_code: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("reconciliation.read")),
) -> list[PurchaseOrder]:
    return list_reconciliation_purchase_orders(
        db,
        completed=queue == "completed",
        search=search,
        date_from=date_from,
        date_to=date_to,
        entity_code=entity_code,
        region_code=region_code,
        store_number=store_number,
        vendor_code=vendor_code,
    )


@router.get("/reconciliation-queue/{order_id}", response_model=PurchaseOrderResponse)
def read_reconciliation_order(
    order_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("reconciliation.read")),
) -> PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order is None or order.status != "awaiting_reconciliation":
        raise HTTPException(status_code=404, detail="Reconciliation purchase order not found")
    return order


@router.post("/{order_id}/reconciliation-handoff", response_model=PurchaseOrderResponse)
def handoff_to_reconciliation(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("purchase_orders.handoff")),
) -> PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    _ensure_order_access(user, order)
    try:
        return handoff_purchase_order(db, order, user.email)
    except PurchaseOrderError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{order_id}", response_model=PurchaseOrderResponse)
def read_order(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PurchaseOrder:
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found"
        )
    _ensure_order_access(user, order)
    return order


@router.post(
    "/{order_id}/artifacts/{artifact_format}",
    response_model=PurchaseOrderArtifactResponse,
)
def create_artifact(
    order_id: str,
    artifact_format: PurchaseOrderArtifactFormat,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PurchaseOrderArtifactResponse:
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found"
        )
    _ensure_order_access(user, order)
    try:
        artifact = generate_artifact(
            db,
            order,
            artifact_format,
            user.email,
            settings.purchase_order_export_path,
        )
    except PurchaseOrderArtifactError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return PurchaseOrderArtifactResponse.model_validate(artifact)


@router.get("/{order_id}/artifacts", response_model=list[PurchaseOrderArtifactResponse])
def read_artifacts(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PurchaseOrderArtifactResponse]:
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found"
        )
    _ensure_order_access(user, order)
    return [
        PurchaseOrderArtifactResponse.model_validate(artifact)
        for artifact in list_artifacts(db, order.id)
    ]


@router.get("/{order_id}/artifacts/{artifact_id}/content")
def download_artifact(
    order_id: str,
    artifact_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found"
        )
    _ensure_order_access(user, order)
    artifact = get_artifact(db, order.id, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    try:
        path = artifact_path(artifact, settings.purchase_order_export_path)
    except PurchaseOrderArtifactError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    return FileResponse(
        path,
        media_type=artifact.content_type,
        filename=f"{order.po_number}.{artifact.artifact_format}",
    )


@router.post(
    "/{order_id}/transmissions",
    response_model=PurchaseOrderTransmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def prepare_transmission(
    order_id: str,
    payload: PurchaseOrderTransmissionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PurchaseOrderTransmissionResponse:
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found"
        )
    _ensure_order_access(user, order)
    try:
        transmission = create_transmission(
            db,
            order,
            payload.artifact_id,
            payload.channel,
            payload.destination,
            payload.notes,
            user.email,
            get_permission_codes(user),
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {exc}",
        ) from exc
    except PurchaseOrderTransmissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PurchaseOrderTransmissionResponse.model_validate(transmission)


@router.get(
    "/{order_id}/transmissions",
    response_model=list[PurchaseOrderTransmissionResponse],
)
def read_transmissions(
    order_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PurchaseOrderTransmissionResponse]:
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found"
        )
    _ensure_order_access(user, order)
    return [
        PurchaseOrderTransmissionResponse.model_validate(item)
        for item in list_transmissions(db, order.id)
    ]


@router.post(
    "/{order_id}/transmissions/{transmission_id}/actions",
    response_model=PurchaseOrderTransmissionResponse,
)
def run_transmission_action(
    order_id: str,
    transmission_id: str,
    payload: PurchaseOrderTransmissionActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PurchaseOrderTransmissionResponse:
    order = get_purchase_order(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase order not found"
        )
    _ensure_order_access(user, order)
    transmission = get_transmission(db, order.id, transmission_id)
    if transmission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transmission not found")
    try:
        updated = apply_transmission_action(
            db,
            order,
            transmission,
            payload.action,
            payload.reason,
            user.email,
            get_permission_codes(user),
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {exc}",
        ) from exc
    except PurchaseOrderTransmissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PurchaseOrderTransmissionResponse.model_validate(updated)
