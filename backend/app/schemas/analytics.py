from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StatusMetric(BaseModel):
    status: str
    count: int


class CurrencyMetric(BaseModel):
    currency: str
    amount: Decimal


class PurchasingKPIs(BaseModel):
    purchase_order_count: int
    purchase_order_statuses: list[StatusMetric]
    ordered_spend: list[CurrencyMetric]


class ReceivingKPIs(BaseModel):
    receipt_count: int
    accepted_quantity: Decimal
    rejected_quantity: Decimal
    open_variance_count: int
    open_backorder_count: int
    outstanding_backorder_quantity: Decimal


class InvoiceKPIs(BaseModel):
    invoice_count: int
    invoice_statuses: list[StatusMetric]
    invoiced_amount: list[CurrencyMetric]
    line_match_exception_count: int


class ReconciliationKPIs(BaseModel):
    case_count: int
    case_statuses: list[StatusMetric]
    open_exception_count: int


class OperationalDashboardResponse(BaseModel):
    purchasing: PurchasingKPIs
    receiving: ReceivingKPIs
    invoices: InvoiceKPIs
    reconciliation: ReconciliationKPIs


class SpendDimension(StrEnum):
    VENDOR = "vendor"
    STORE = "store"
    WORKFLOW = "workflow"
    CATEGORY = "category"
    MONTH = "month"


class SpendMetric(BaseModel):
    dimension_key: str
    currency: str
    purchase_order_count: int
    line_count: int
    quantity: Decimal
    amount: Decimal


class SpendAnalysisResponse(BaseModel):
    group_by: SpendDimension
    date_from: datetime | None
    date_to: datetime | None
    metrics: list[SpendMetric]


class VendorScorecard(BaseModel):
    vendor_code: str
    vendor_name: str
    purchase_order_count: int
    ordered_spend: list[CurrencyMetric]
    acknowledgement_count: int
    accepted_acknowledgement_count: int
    rejected_acknowledgement_count: int
    acknowledgement_coverage_rate: Decimal | None
    measured_delivery_count: int
    on_time_delivery_count: int
    on_time_delivery_rate: Decimal | None
    accepted_quantity: Decimal
    rejected_quantity: Decimal
    receiving_acceptance_rate: Decimal | None
    invoice_line_count: int
    matched_invoice_line_count: int
    invoice_match_rate: Decimal | None
    approved_reconciliation_count: int
    rejected_reconciliation_count: int


class VendorScorecardResponse(BaseModel):
    date_from: datetime | None
    date_to: datetime | None
    scorecards: list[VendorScorecard]


class ApprovalActorMetric(BaseModel):
    actor: str
    approval_count: int
    rejection_count: int


class WorkflowMetric(BaseModel):
    workflow_code: str
    instance_count: int
    active_count: int
    completed_count: int
    current_states: list[StatusMetric]
    transition_count: int
    approval_count: int
    rejection_count: int
    average_completion_seconds: Decimal | None
    median_completion_seconds: Decimal | None
    p90_completion_seconds: Decimal | None
    approval_actors: list[ApprovalActorMetric]


class WorkflowAnalyticsResponse(BaseModel):
    date_from: datetime | None
    date_to: datetime | None
    workflows: list[WorkflowMetric]


class InventoryPositionMetric(BaseModel):
    store_number: str
    product_code: str
    product_name: str
    accepted_quantity: Decimal
    rejected_quantity: Decimal
    outstanding_backorder_quantity: Decimal


class InventoryPositionResponse(BaseModel):
    positions: list[InventoryPositionMetric]


class AnalyticsReportType(StrEnum):
    INVENTORY_POSITION = "inventory_position"
    SPEND = "spend"
    VENDOR_SCORECARDS = "vendor_scorecards"
    WORKFLOWS = "workflows"


class AnalyticsReportScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    report_type: AnalyticsReportType
    parameters: dict[str, str] = Field(default_factory=dict)
    interval_minutes: int = Field(ge=5, le=43200)
    next_run_at: datetime | None = None
    is_enabled: bool = True

    @model_validator(mode="after")
    def validate_parameters(self) -> "AnalyticsReportScheduleCreate":
        allowed = {
            AnalyticsReportType.INVENTORY_POSITION: {"store_number", "product_code"},
            AnalyticsReportType.SPEND: {
                "group_by",
                "vendor_code",
                "store_number",
                "workflow_code",
            },
            AnalyticsReportType.VENDOR_SCORECARDS: {"minimum_orders"},
            AnalyticsReportType.WORKFLOWS: {"workflow_code"},
        }[self.report_type]
        unknown = set(self.parameters) - allowed
        if unknown:
            raise ValueError(f"Unsupported report parameters: {', '.join(sorted(unknown))}")
        if any(len(key) > 64 or len(value) > 256 for key, value in self.parameters.items()):
            raise ValueError("Report parameter names or values exceed their maximum length")
        group_by = self.parameters.get("group_by")
        if group_by is not None:
            try:
                SpendDimension(group_by)
            except ValueError as exc:
                raise ValueError("Spend report group_by parameter is invalid") from exc
        minimum_orders = self.parameters.get("minimum_orders")
        if minimum_orders is not None:
            try:
                valid_minimum = int(minimum_orders) >= 1
            except ValueError:
                valid_minimum = False
            if not valid_minimum:
                raise ValueError("minimum_orders must be a positive integer")
        return self


class AnalyticsReportScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    report_type: AnalyticsReportType
    parameters: dict[str, str]
    interval_minutes: int
    next_run_at: datetime
    is_enabled: bool
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


class AnalyticsReportRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    schedule_id: str
    scheduled_for: datetime
    status: str
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    error_message: str | None
    created_by: str
    created_at: datetime
    completed_at: datetime | None
