from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class PurchaseOrderArtifactFormat(StrEnum):
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"


class PurchaseOrderArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    purchase_order_id: str
    artifact_format: PurchaseOrderArtifactFormat
    version: int
    content_type: str
    size_bytes: int
    sha256: str
    created_by: str
    created_at: datetime
