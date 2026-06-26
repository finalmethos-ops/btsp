from datetime import datetime

from pydantic import BaseModel

from app.schemas.store import StoreUpsert


class StoreBatchRow(StoreUpsert):
    row_number: int | None = None


class StoreBatchRequest(BaseModel):
    source_system: str = "official_store_database"
    submitted_by: str
    rows: list[StoreBatchRow]


class StoreBatchError(BaseModel):
    row_number: int | None
    store_number: str | None
    message: str


class StoreBatchResult(BaseModel):
    source_system: str
    submitted_by: str
    processed_at: datetime
    total_rows: int
    upserted_rows: int
    failed_rows: int
    errors: list[StoreBatchError]
