from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.core.workflows import WORKFLOW_REGISTRY
from app.models.identity import User
from app.schemas.workflow_registry import (
    AvailableWorkflowResponse,
    WorkflowRegistryEntryResponse,
)
from app.services.auth_service import user_workflow_codes

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/available", response_model=list[AvailableWorkflowResponse])
def read_available_workflows(
    current_user: User = Depends(get_current_user),
) -> list[AvailableWorkflowResponse]:
    registrations = (
        WORKFLOW_REGISTRY.get(workflow_code) for workflow_code in user_workflow_codes(current_user)
    )
    return [
        AvailableWorkflowResponse.model_validate(registration)
        for registration in registrations
        if registration is not None and registration.is_active
    ]


@router.get("/registry", response_model=list[WorkflowRegistryEntryResponse])
def read_workflow_registry(
    _current_user: User = Depends(require_permission("workflows.read")),
) -> list[WorkflowRegistryEntryResponse]:
    return [
        WorkflowRegistryEntryResponse.model_validate(registration)
        for registration in WORKFLOW_REGISTRY.list()
    ]
