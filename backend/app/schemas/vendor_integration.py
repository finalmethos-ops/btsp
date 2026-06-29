from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.vendor_connector_security import configuration_contains_secret


class VendorTransport(StrEnum):
    REST_API = "rest_api"
    SFTP = "sftp"
    EDI = "edi"
    MANUAL_IMPORT = "manual_import"


class VendorEndpointDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class VendorEventType(StrEnum):
    ACKNOWLEDGEMENT = "acknowledgement"
    SHIPMENT_UPDATE = "shipment_update"
    ASN = "asn"


class VendorAcknowledgementStatus(StrEnum):
    ACCEPTED = "accepted"
    ACCEPTED_WITH_CHANGES = "accepted_with_changes"
    REJECTED = "rejected"


class VendorShipmentStatus(StrEnum):
    PLANNED = "planned"
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class VendorEndpointCreate(BaseModel):
    vendor_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    transport: VendorTransport
    direction: VendorEndpointDirection
    external_vendor_id: str | None = Field(default=None, max_length=128)
    connection_reference: str | None = Field(default=None, max_length=255)
    configuration: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("configuration")
    @classmethod
    def reject_embedded_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        if configuration_contains_secret(value):
            raise ValueError("Endpoint configuration must not contain connector secrets")
        return value


class VendorEndpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vendor_code: str
    name: str
    transport: VendorTransport
    direction: VendorEndpointDirection
    external_vendor_id: str | None
    connection_reference: str | None
    configuration: dict[str, Any]
    is_active: bool
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class VendorInboundEventCreate(BaseModel):
    endpoint_id: str
    external_event_id: str = Field(min_length=1, max_length=160)
    event_type: VendorEventType
    payload: dict[str, Any]
    occurred_at: datetime | None = None


class VendorImportEvent(BaseModel):
    external_event_id: str = Field(min_length=1, max_length=160)
    event_type: VendorEventType
    payload: dict[str, Any]
    occurred_at: datetime | None = None


class VendorConnectorImportRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    endpoint_id: str
    source_name: str
    content_type: str | None
    content_sha256: str
    status: str
    event_count: int
    error_message: str | None
    imported_by: str
    created_at: datetime
    completed_at: datetime | None


class VendorConnectorScheduleCreate(BaseModel):
    endpoint_id: str
    name: str = Field(min_length=1, max_length=128)
    interval_minutes: int = Field(ge=1, le=10080)
    max_attempts: int = Field(default=3, ge=1, le=10)
    base_retry_seconds: int = Field(default=60, ge=5, le=86400)
    is_enabled: bool = True
    next_run_at: datetime | None = None


class VendorConnectorScheduleUpdate(BaseModel):
    is_enabled: bool | None = None
    next_run_at: datetime | None = None

    @model_validator(mode="after")
    def require_change(self) -> "VendorConnectorScheduleUpdate":
        if self.is_enabled is None and self.next_run_at is None:
            raise ValueError("At least one schedule change is required")
        return self


class VendorConnectorScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    endpoint_id: str
    name: str
    interval_minutes: int
    max_attempts: int
    base_retry_seconds: int
    is_enabled: bool
    next_run_at: datetime
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class VendorConnectorExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    schedule_id: str
    endpoint_id: str
    import_run_id: str | None
    status: str
    scheduled_for: datetime
    available_at: datetime
    attempt_count: int
    max_attempts: int
    worker_id: str | None
    lease_expires_at: datetime | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class VendorConnectorClaimRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=160)
    lease_seconds: int = Field(default=300, ge=30, le=3600)


class VendorConnectorClaimResponse(VendorConnectorExecutionResponse):
    lease_token: str
    endpoint_transport: VendorTransport
    endpoint_connection_reference: str | None
    endpoint_configuration: dict[str, Any]


class VendorConnectorExecutionResult(BaseModel):
    lease_token: str = Field(min_length=32, max_length=64)
    succeeded: bool
    import_run_id: str | None = None
    error_message: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_result(self) -> "VendorConnectorExecutionResult":
        if self.succeeded and self.error_message:
            raise ValueError("Successful connector execution cannot include an error")
        if not self.succeeded and not self.error_message:
            raise ValueError("Failed connector execution requires an error")
        return self


class VendorInboundEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    endpoint_id: str
    vendor_code: str
    external_event_id: str
    event_type: VendorEventType
    payload: dict[str, Any]
    payload_sha256: str
    status: str
    occurred_at: datetime | None
    received_by: str
    received_at: datetime
    processed_at: datetime | None
    error_message: str | None


class VendorAcknowledgementPayload(BaseModel):
    purchase_order_number: str = Field(min_length=1, max_length=64)
    acknowledgement_status: VendorAcknowledgementStatus
    vendor_reference: str | None = Field(default=None, max_length=160)
    acknowledged_at: datetime | None = None
    expected_ship_date: datetime | None = None
    reason: str | None = Field(default=None, max_length=1000)
    changes: list[dict[str, Any]] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def validate_outcome_details(self) -> "VendorAcknowledgementPayload":
        if self.acknowledgement_status is VendorAcknowledgementStatus.REJECTED and not self.reason:
            raise ValueError("Rejected acknowledgement requires a reason")
        if (
            self.acknowledgement_status is VendorAcknowledgementStatus.ACCEPTED_WITH_CHANGES
            and not self.changes
        ):
            raise ValueError("Accepted-with-changes acknowledgement requires change details")
        return self


class VendorAcknowledgementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inbound_event_id: str
    endpoint_id: str
    purchase_order_id: str
    vendor_code: str
    acknowledgement_status: VendorAcknowledgementStatus
    vendor_reference: str | None
    acknowledged_at: datetime | None
    expected_ship_date: datetime | None
    reason: str | None
    changes: list[dict[str, Any]]
    created_by: str
    created_at: datetime


class VendorShipmentUpdatePayload(BaseModel):
    purchase_order_number: str = Field(min_length=1, max_length=64)
    shipment_number: str = Field(min_length=1, max_length=160)
    status: VendorShipmentStatus
    carrier: str | None = Field(default=None, max_length=160)
    tracking_number: str | None = Field(default=None, max_length=160)
    estimated_delivery_at: datetime | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)


class VendorShipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    purchase_order_id: str
    vendor_code: str
    shipment_number: str
    status: VendorShipmentStatus
    carrier: str | None
    tracking_number: str | None
    estimated_delivery_at: datetime | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VendorASNLinePayload(BaseModel):
    purchase_order_line_id: int
    product_code: str = Field(min_length=1, max_length=64)
    quantity: float = Field(gt=0)
    lot_number: str | None = Field(default=None, max_length=160)


class VendorASNPayload(BaseModel):
    purchase_order_number: str = Field(min_length=1, max_length=64)
    asn_number: str = Field(min_length=1, max_length=160)
    shipment_number: str | None = Field(default=None, max_length=160)
    expected_delivery_at: datetime | None = None
    lines: list[VendorASNLinePayload] = Field(min_length=1, max_length=1000)


class VendorASNLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_order_line_id: int
    product_code: str
    quantity: float
    lot_number: str | None


class VendorASNResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inbound_event_id: str
    purchase_order_id: str
    shipment_id: str | None
    vendor_code: str
    asn_number: str
    expected_delivery_at: datetime | None
    status: str
    created_by: str
    created_at: datetime
    lines: list[VendorASNLineResponse]
