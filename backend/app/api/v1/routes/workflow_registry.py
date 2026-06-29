from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.permissions import require_permission
from app.core.workflows import WORKFLOW_REGISTRY, WorkflowRegistryError
from app.models.identity import User
from app.schemas.workflow_registry import WorkflowRegistryEntryResponse

router = APIRouter(prefix="/workflow-registry", tags=["workflow-registry"])


@router.post("/seeds/defaults")
def seed_workflow_registry_defaults(
    _current_user: User = Depends(require_permission("configuration.manage")),
) -> dict[str, int]:
    return {"seeded_count": len(WORKFLOW_REGISTRY.list())}


@router.get("", response_model=list[WorkflowRegistryEntryResponse])
def read_workflow_registry(
    _current_user: User = Depends(require_permission("workflows.read")),
) -> list[WorkflowRegistryEntryResponse]:
    return [
        WorkflowRegistryEntryResponse.model_validate(registration)
        for registration in WORKFLOW_REGISTRY.list()
    ]


@router.get("/{workflow_code}", response_model=WorkflowRegistryEntryResponse)
def read_workflow_registry_entry(
    workflow_code: str,
    _current_user: User = Depends(require_permission("workflows.read")),
) -> WorkflowRegistryEntryResponse:
    try:
        registration = WORKFLOW_REGISTRY.require(workflow_code)
    except WorkflowRegistryError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return WorkflowRegistryEntryResponse.model_validate(registration)
