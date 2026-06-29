from app.core.workflows import WORKFLOW_REGISTRY
from app.schemas.workflow_registry import (
    AvailableWorkflowResponse,
    WorkflowRegistryEntryResponse,
)


def test_available_workflow_response_maps_registry_metadata() -> None:
    registration = WORKFLOW_REGISTRY.require("BPP")

    response = AvailableWorkflowResponse.model_validate(registration)

    assert response.model_dump() == {
        "code": "BPP",
        "name": "BPP Ordering",
        "route": "/workflows/bpp",
    }


def test_registry_response_includes_permission_code() -> None:
    registration = WORKFLOW_REGISTRY.require("INDEPENDENT")

    response = WorkflowRegistryEntryResponse.model_validate(registration)

    assert response.permission_code == "orders.independent.manage"
