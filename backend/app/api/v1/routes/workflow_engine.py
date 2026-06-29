from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import get_permission_codes, require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.bpp_purchasing import BppPurchasingSeedResponse
from app.schemas.flow import (
    FlowActionRequest,
    FlowDefinitionResponse,
    FlowDefinitionWrite,
    FlowInstanceResponse,
    FlowStartRequest,
)
from app.schemas.independent_purchasing import IndependentPurchasingSeedResponse
from app.services.bpp_purchasing_seed_service import seed_bpp_purchasing
from app.services.independent_seed_service import seed_independent_purchasing
from app.services.store_service import check_region_scope
from app.services.workflow_engine import (
    WorkflowError,
    advance_workflow,
    start_workflow,
    upsert_workflow_definition,
)

router = APIRouter(prefix="/workflow-engine", tags=["workflow-engine"])


@router.post("/seeds/bpp-purchasing", response_model=BppPurchasingSeedResponse)
def seed_bpp_purchasing_workflow(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("configuration.manage")),
) -> BppPurchasingSeedResponse:
    return seed_bpp_purchasing(db, actor=current_user.email)


@router.post("/seeds/ind-purchasing", response_model=IndependentPurchasingSeedResponse)
def seed_independent_purchasing_workflow(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("configuration.manage")),
) -> IndependentPurchasingSeedResponse:
    return seed_independent_purchasing(db, actor=current_user.email)


@router.post("/definitions", response_model=FlowDefinitionResponse)
def write_definition(
    payload: FlowDefinitionWrite,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("configuration.manage")),
) -> FlowDefinitionResponse:
    definition = upsert_workflow_definition(db, payload)
    return FlowDefinitionResponse(
        id=definition.id,
        code=definition.code,
        name=definition.name,
        version=definition.version,
        business_area=definition.business_area,
        category=definition.category,
        configuration_namespace=definition.configuration_namespace,
        states=definition.states,
        initial_state=definition.initial_state,
        terminal_states=definition.terminal_states,
        rules=payload.rules,
        is_active=definition.is_active,
        created_at=definition.created_at,
        updated_at=definition.updated_at,
    )


@router.post("/instances", response_model=FlowInstanceResponse)
def start_instance(
    payload: FlowStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlowInstanceResponse:
    if payload.workflow_code == "IND_PURCHASING":
        permission_codes = get_permission_codes(current_user)
        if "workflow.ind.submit" not in permission_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing required permission: workflow.ind.submit",
            )
        store_number = payload.context.get("store_number")
        if not isinstance(store_number, str) or not store_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Independent purchasing requires context.store_number",
            )
        if current_user.region_code is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Independent purchasing requires an assigned user region",
            )
        blocked = check_region_scope(db, current_user.region_code, [store_number])
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Store is not active, orderable, or within the user's region",
            )
    try:
        return start_workflow(db, payload, actor=current_user.email)
    except WorkflowError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/instances/{instance_id}/actions", response_model=FlowInstanceResponse)
def run_action(
    instance_id: int,
    payload: FlowActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlowInstanceResponse:
    trusted_payload = payload.model_copy(update={"actor": current_user.email})
    try:
        return advance_workflow(
            db=db,
            instance_id=instance_id,
            payload=trusted_payload,
            permission_codes=get_permission_codes(current_user),
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {exc}",
        ) from exc
    except WorkflowError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
