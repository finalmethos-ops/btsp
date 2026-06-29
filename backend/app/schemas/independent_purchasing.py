from pydantic import BaseModel


class IndependentPurchasingSeedResponse(BaseModel):
    workflow_code: str
    workflow_version: int
    permissions_seeded: int
    configuration_entries_seeded: int
    approval_entries_seeded: int
    notification_templates_seeded: int
    registry_entry_verified: bool
