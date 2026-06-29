from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class AttachmentCategory(StrEnum):
    QUOTE = "quote"
    VENDOR_DOCUMENT = "vendor_document"
    IMAGE = "image"
    PDF = "pdf"
    SUPPORTING_DOCUMENT = "supporting_document"


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    purchase_request_id: str
    category: AttachmentCategory
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_by: str
    created_at: datetime
