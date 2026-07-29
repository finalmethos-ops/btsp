from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import CatalogProduct
from app.models.invoice_intake import InvoiceIntakeDocument
from app.models.purchase_order import PurchaseOrder
from app.schemas.vendor_report import (
    CurrencyMetric,
    MonthlyVendorSpend,
    VendorCategorySpend,
    VendorReportResponse,
)


def build_vendor_report(
    db: Session, vendor_code: str, year: int | None = None
) -> VendorReportResponse:
    all_orders = list(
        db.scalars(
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.lines))
            .where(PurchaseOrder.vendor_code == vendor_code)
            .order_by(PurchaseOrder.created_at)
        )
        .unique()
        .all()
    )
    available_years = sorted({order.created_at.year for order in all_orders}, reverse=True)
    selected_year = year or (available_years[0] if available_years else datetime.now(UTC).year)
    orders = [order for order in all_orders if order.created_at.year == selected_year]
    product_codes = {line.product_code for order in orders for line in order.lines}
    products = {
        product.product_code: product
        for product in db.scalars(
            select(CatalogProduct).where(CatalogProduct.product_code.in_(product_codes))
        ).all()
    }

    annual: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    po_counts: dict[str, int] = defaultdict(int)
    monthly: dict[tuple[int, str], dict[str, Decimal | set[str]]] = {}
    categories: dict[tuple[str, str, str], dict[str, Decimal | set[str]]] = {}
    units_ordered = Decimal("0")
    units_received = Decimal("0")
    for order in orders:
        annual[order.currency] += order.total
        po_counts[order.currency] += 1
        month_key = (order.created_at.month, order.currency)
        month = monthly.setdefault(
            month_key,
            {
                "orders": set(),
                "quantity": Decimal("0"),
                "received": Decimal("0"),
                "spend": Decimal("0"),
            },
        )
        cast_orders = cast(set[str], month["orders"])
        cast_orders.add(order.id)
        month["spend"] = Decimal(month["spend"]) + order.total
        for line in order.lines:
            units_ordered += line.quantity
            units_received += line.received_quantity
            month["quantity"] = Decimal(month["quantity"]) + line.quantity
            month["received"] = Decimal(month["received"]) + line.received_quantity
            product = products.get(line.product_code)
            department = product.department if product and product.department else "UNASSIGNED"
            category_code = (
                product.product_category_code
                if product and product.product_category_code
                else "UNASSIGNED"
            )
            category = categories.setdefault(
                (department, category_code, order.currency),
                {"orders": set(), "quantity": Decimal("0"), "spend": Decimal("0")},
            )
            category_orders = cast(set[str], category["orders"])
            category_orders.add(order.id)
            category["quantity"] = Decimal(category["quantity"]) + line.quantity
            category["spend"] = Decimal(category["spend"]) + line.extended_amount

    invoice_count = (
        db.scalar(
            select(func.count())
            .select_from(InvoiceIntakeDocument)
            .where(
                InvoiceIntakeDocument.detected_vendor_code == vendor_code,
                InvoiceIntakeDocument.status.in_({"unreconciled", "paired"}),
            )
        )
        or 0
    )
    active_statuses = {"active", "awaiting_vendor_acceptance"}
    attention_statuses = {"vendor_attention", "purchasing_attention"}
    inactive_statuses = {"vendor_rejected", "cancelled"}
    return VendorReportResponse(
        vendor_code=vendor_code,
        selected_year=selected_year,
        available_years=available_years or [selected_year],
        purchase_order_count=len(orders),
        active_po_count=sum(order.status in active_statuses for order in orders),
        attention_po_count=sum(order.status in attention_statuses for order in orders),
        rejected_or_cancelled_count=sum(order.status in inactive_statuses for order in orders),
        units_ordered=units_ordered,
        units_received=units_received,
        fill_rate=(units_received / units_ordered * 100) if units_ordered else None,
        unreconciled_invoice_count=int(invoice_count),
        annual_spend=[
            CurrencyMetric(currency=currency, amount=amount)
            for currency, amount in sorted(annual.items())
        ],
        average_po_value=[
            CurrencyMetric(currency=currency, amount=annual[currency] / count)
            for currency, count in sorted(po_counts.items())
        ],
        monthly_spend=[
            MonthlyVendorSpend(
                month=month_number,
                currency=currency,
                purchase_order_count=len(values["orders"]),  # type: ignore[arg-type]
                quantity=Decimal(values["quantity"]),
                received_quantity=Decimal(values["received"]),
                spend=Decimal(values["spend"]),
            )
            for (month_number, currency), values in sorted(monthly.items())
        ],
        category_spend=[
            VendorCategorySpend(
                department=department,
                product_code=product_code,
                currency=currency,
                purchase_order_count=len(values["orders"]),  # type: ignore[arg-type]
                quantity=Decimal(values["quantity"]),
                spend=Decimal(values["spend"]),
            )
            for (department, product_code, currency), values in sorted(categories.items())
        ],
    )
