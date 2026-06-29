from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FlowRule(BaseModel):
    action: str
    source: str
    target: str
    permission: str | None = None


class FlowDefinitionWrite(BaseModel):
    code: str
    name: str
    version: int = 1
    business_area: str | None = None
    category: str | None = None
    configuration_namespace: str | None = None
    states: list[str] = Field(default_factory=list)
    initial_state: str
    terminal_states: list[str] = Field(default_factory=list)
    rules: list[FlowRule]
    is_active: bool = True


class FlowDefinitionResponse(FlowDefinitionWrite):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FlowStartRequest(BaseModel):
    workflow_code: str
    entity_type: str
    entity_id: str
    context: dict[str, Any] = Field(default_factory=dict)


class FlowActionRequest(BaseModel):
    action: str
    actor: str
    context_patch: dict[str, Any] = Field(default_factory=dict)


class FlowInstanceResponse(BaseModel):
    id: int
    workflow_code: str
    workflow_version: int
    entity_type: str
    entity_id: str
    current_state: str
    status: str
    context: dict[str, Any]
    started_by: str
    updated_by: str
    started_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
