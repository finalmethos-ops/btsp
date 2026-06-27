from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import get_permission_codes, require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.flow import (
    FlowActionRequest,
    FlowDefinitionResponse,
    FlowDefinitionWrite,
    FlowInstanceResponse,
    FlowStartRequest,
)
from app.services.workflow_engine import (
    WorkflowError,
    advance_workflow,
    start_workflow,
    upsert_workflow_definition,
)

router = APIRouter(prefix="/workflow-engine", tags=["workflow-engine"])


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
