from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ApprovalLevel(StrEnum):
    NONE = "none"
    STORE = "store"
    DEPARTMENT = "department"
    FRANCHISE = "franchise"
    PURCHASING = "purchasing"
    EXECUTIVE = "executive"
    REGIONAL = "regional"
    SYSTEM_ADMIN = "system_admin"


class ApprovalPolicyInput(BaseModel):
    workflow_code: str
    entity_type: str
    entity_id: str
    request_amount: Decimal = Field(ge=0)
    region_code: str | None = None
    store_number: str | None = None
    vendor_code: str | None = None
    product_category: str | None = None
    buying_group_code: str | None = None
    submitted_by: str
    context: dict[str, Any] = Field(default_factory=dict)


class ApprovalPolicyMatch(BaseModel):
    policy_code: str
    approval_level: ApprovalLevel
    approval_reason: str
    required_permission: str
    routing_group: str


class ApprovalPolicyResult(BaseModel):
    requires_approval: bool
    approval_level: ApprovalLevel
    approval_reason: str | None
    required_permission: str | None
    routing_group: str | None
    matched_policy_codes: list[str]
