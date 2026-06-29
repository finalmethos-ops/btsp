from pydantic import BaseModel


class AvailableWorkflowResponse(BaseModel):
    code: str
    name: str
    route: str

    model_config = {"from_attributes": True}


class WorkflowRegistryEntryResponse(AvailableWorkflowResponse):
    permission_code: str
    business_area: str | None
    category: str | None
    configuration_namespace: str | None
    is_active: bool
    lifecycle: str
