from datetime import datetime
from typing import Any

from pydantic import BaseModel


class WorkflowDefinitionAdminResponse(BaseModel):
    id: int
    code: str
    name: str
    version: int
    business_area: str | None
    category: str | None
    configuration_namespace: str | None
    states: list[str]
    initial_state: str
    terminal_states: list[str]
    transitions: list[dict[str, Any]]
    is_active: bool
    active_instance_count: int
    total_instance_count: int
    created_at: datetime
    updated_at: datetime


class WorkflowActivationUpdate(BaseModel):
    is_active: bool
