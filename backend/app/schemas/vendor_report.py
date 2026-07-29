from decimal import Decimal

from pydantic import BaseModel


class CurrencyMetric(BaseModel):
    currency: str
    amount: Decimal


class MonthlyVendorSpend(BaseModel):
    month: int
    currency: str
    purchase_order_count: int
    quantity: Decimal
    received_quantity: Decimal
    spend: Decimal


class VendorCategorySpend(BaseModel):
    department: str
    product_code: str
    currency: str
    purchase_order_count: int
    quantity: Decimal
    spend: Decimal


class VendorReportResponse(BaseModel):
    vendor_code: str
    selected_year: int
    available_years: list[int]
    purchase_order_count: int
    active_po_count: int
    attention_po_count: int
    rejected_or_cancelled_count: int
    units_ordered: Decimal
    units_received: Decimal
    fill_rate: Decimal | None
    unreconciled_invoice_count: int
    annual_spend: list[CurrencyMetric]
    average_po_value: list[CurrencyMetric]
    monthly_spend: list[MonthlyVendorSpend]
    category_spend: list[VendorCategorySpend]
