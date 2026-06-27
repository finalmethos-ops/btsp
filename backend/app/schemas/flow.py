from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FlowRule(BaseModel):
    action: str
    source: str
    target: str
    permission: str | None = None


class FlowDefinitionWrite(BaseModel):
    code: str
    name: str
    version: int = 1
    initial_state: str
    terminal_states: list[str] = []
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
    context: dict[str, Any] = {}


class FlowActionRequest(BaseModel):
    action: str
    actor: str
    context_patch: dict[str, Any] = {}


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
