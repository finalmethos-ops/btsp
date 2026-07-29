from datetime import date, datetime, time

from sqlalchemy import Select, select

from app.models.purchase_order import PurchaseOrder, PurchaseOrderSource
from app.models.store import Store


def apply_purchase_order_filters(
    statement: Select,
    *,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    entity_code: str | None = None,
    region_code: str | None = None,
    store_number: str | None = None,
    vendor_code: str | None = None,
) -> Select:
    if search and search.strip():
        statement = statement.where(PurchaseOrder.po_number.ilike(f"%{search.strip()}%"))
    if date_from:
        statement = statement.where(
            PurchaseOrder.created_at >= datetime.combine(date_from, time.min)
        )
    if date_to:
        statement = statement.where(PurchaseOrder.created_at <= datetime.combine(date_to, time.max))
    if vendor_code:
        statement = statement.where(PurchaseOrder.vendor_code == vendor_code)
    if entity_code or region_code or store_number:
        matching_orders = select(PurchaseOrderSource.purchase_order_id).join(
            Store, Store.store_number == PurchaseOrderSource.store_number
        )
        if entity_code:
            matching_orders = matching_orders.where(Store.entity_code == entity_code)
        if region_code:
            matching_orders = matching_orders.where(Store.region_code == region_code)
        if store_number:
            matching_orders = matching_orders.where(Store.store_number == store_number)
        statement = statement.where(PurchaseOrder.id.in_(matching_orders))
    return statement
