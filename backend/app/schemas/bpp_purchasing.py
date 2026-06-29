from pydantic import BaseModel


class BppPurchasingSeedResponse(BaseModel):
    workflow_code: str
    workflow_version: int
    permissions_seeded: int
    configuration_entries_seeded: int
    registry_entry_verified: bool
