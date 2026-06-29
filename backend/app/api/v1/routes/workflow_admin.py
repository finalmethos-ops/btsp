from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.workflow_admin import (
    WorkflowActivationUpdate,
    WorkflowDefinitionAdminResponse,
)
from app.services.workflow_admin_service import (
    WorkflowAdminError,
    list_workflow_definitions,
    set_workflow_activation,
)

router = APIRouter(prefix="/workflow-admin", tags=["workflow administration"])


@router.get("/definitions", response_model=list[WorkflowDefinitionAdminResponse])
def read_workflow_definitions(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("workflows.manage")),
) -> list[WorkflowDefinitionAdminResponse]:
    return list_workflow_definitions(db)


@router.patch(
    "/definitions/{workflow_code}/versions/{version}/activation",
    response_model=WorkflowDefinitionAdminResponse,
)
def patch_workflow_activation(
    workflow_code: str,
    version: int,
    payload: WorkflowActivationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("workflows.manage")),
) -> WorkflowDefinitionAdminResponse:
    try:
        definition = set_workflow_activation(
            db, workflow_code, version, payload.is_active, user.email
        )
    except WorkflowAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow definition version not found",
        )
    return definition
