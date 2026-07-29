from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InventoryLedgerEntryCreate(BaseModel):
    product_code: str = Field(min_length=1, max_length=64)
    store_number: str = Field(min_length=1, max_length=32)
    quantity_delta: Decimal
    reason: str = Field(min_length=1, max_length=32)
    reference_type: str | None = Field(default=None, max_length=64)
    reference_id: str | None = Field(default=None, max_length=128)


class InventoryLedgerEntryResponse(InventoryLedgerEntryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor: str
    created_at: datetime


class InventoryPositionResponse(BaseModel):
    product_code: str
    store_number: str
    on_hand: Decimal
    reserved: Decimal
    available: Decimal


class InventoryReservationCreate(BaseModel):
    product_code: str = Field(min_length=1, max_length=64)
    store_number: str = Field(min_length=1, max_length=32)
    quantity: Decimal = Field(gt=0)


class InventoryReservationResponse(InventoryReservationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    created_by: str
    created_at: datetime
    released_at: datetime | None


class InventoryTransferCreate(BaseModel):
    product_code: str = Field(min_length=1, max_length=64)
    from_store_number: str = Field(min_length=1, max_length=32)
    to_store_number: str = Field(min_length=1, max_length=32)
    quantity: Decimal = Field(gt=0)


class InventoryTransferResponse(InventoryTransferCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    created_by: str
    created_at: datetime
