from decimal import Decimal

from app.models.event_management import EventEntityOrder


def allocation_is_initialized(order: EventEntityOrder) -> bool:
    return (order.confirmed_quantity or 0) + (order.waitlisted_quantity or 0) == order.quantity


def confirmed_quantity(order: EventEntityOrder) -> int:
    if allocation_is_initialized(order):
        return int(order.confirmed_quantity or 0)
    return order.quantity if order.status == "confirmed" else 0


def waitlisted_quantity(order: EventEntityOrder) -> int:
    if allocation_is_initialized(order):
        return int(order.waitlisted_quantity or 0)
    return order.quantity if order.status == "waitlisted" else 0


def confirmed_total_cost(order: EventEntityOrder) -> Decimal:
    if allocation_is_initialized(order):
        return Decimal(order.confirmed_total_cost or 0)
    return order.total_cost if order.status == "confirmed" else Decimal("0")


def waitlisted_total_cost(order: EventEntityOrder) -> Decimal:
    if allocation_is_initialized(order):
        return Decimal(order.waitlisted_total_cost or 0)
    return order.total_cost if order.status == "waitlisted" else Decimal("0")


def confirmed_variant_quantities(order: EventEntityOrder) -> dict[str, int]:
    if allocation_is_initialized(order):
        return dict(order.confirmed_variant_quantities or {})
    return dict(order.variant_quantities or {}) if order.status == "confirmed" else {}


def waitlisted_variant_quantities(order: EventEntityOrder) -> dict[str, int]:
    if allocation_is_initialized(order):
        return dict(order.waitlisted_variant_quantities or {})
    return dict(order.variant_quantities or {}) if order.status == "waitlisted" else {}
