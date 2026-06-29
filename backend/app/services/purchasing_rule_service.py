from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.models.purchasing import PurchaseRequest
from app.services.configuration_service import list_config_entries, upsert_config_entry
from app.services.purchasing_defaults import PURCHASING_RULE_DEFAULTS, purchasing_default_entries


@dataclass
class RuleIssue:
    code: str
    message: str
    field: str | None = None


@dataclass
class RuleEvaluation:
    errors: list[RuleIssue] = field(default_factory=list)
    warnings: list[RuleIssue] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.errors


def seed_purchasing_defaults(db: Session, actor: str) -> int:
    entries = purchasing_default_entries(actor)
    for entry in entries:
        upsert_config_entry(db, entry)
    return len(entries)


def load_purchasing_rules(db: Session, workflow_code: str) -> dict[str, dict[str, Any]]:
    rules = {key: dict(value) for key, value in PURCHASING_RULE_DEFAULTS.items()}
    for entry in list_config_entries(db, "purchasing", workflow_code):
        if entry.key in rules and isinstance(entry.value, dict):
            rules[entry.key] = entry.value
    return rules


def _values(config: dict[str, dict[str, Any]], key: str, field_name: str) -> set[str]:
    raw = config.get(key, {}).get(field_name, [])
    if not isinstance(raw, list):
        return set()
    return {str(value).strip().casefold() for value in raw if str(value).strip()}


def evaluate_purchase_request(
    request: PurchaseRequest,
    store_region: str,
    buying_group: str | None,
    config: dict[str, dict[str, Any]],
) -> RuleEvaluation:
    result = RuleEvaluation()
    enabled = config.get("rules.enabled", {}).get("enabled")
    if not isinstance(enabled, bool):
        result.errors.append(
            RuleIssue("configuration.invalid", "Purchasing rules enabled flag is invalid")
        )
        return result
    if not enabled:
        return result
    list_rules = {
        "rules.blocked_stores": "store_numbers",
        "rules.blocked_vendors": "vendor_codes",
        "rules.blocked_products": "product_codes",
        "rules.blocked_categories": "categories",
        "rules.blocked_brands": "brands",
        "rules.allowed_regions": "region_codes",
        "rules.allowed_buying_groups": "buying_group_codes",
        "rules.required_attachment_categories": "categories",
    }
    for key, value_key in list_rules.items():
        if not isinstance(config.get(key, {}).get(value_key), list):
            result.errors.append(
                RuleIssue("configuration.invalid", f"Purchasing rule {key} is invalid")
            )
    if result.errors:
        return result
    if not request.line_items:
        result.errors.append(
            RuleIssue("lines.required", "At least one line item is required", "line_items")
        )
    try:
        minimum = Decimal(str(config["rules.minimum_order_amount"].get("amount", 0)))
    except (InvalidOperation, TypeError):
        result.errors.append(
            RuleIssue("configuration.invalid", "Minimum order amount configuration is invalid")
        )
        minimum = Decimal("0")
    if request.total < minimum:
        result.errors.append(
            RuleIssue("order.minimum", f"Order total must be at least {minimum}", "total")
        )
    blocked = {
        "store_number": ("rules.blocked_stores", "store_numbers", request.store_number),
        "vendor_code": ("rules.blocked_vendors", "vendor_codes", request.vendor_code),
    }
    for field_name, (key, value_key, current) in blocked.items():
        if current.casefold() in _values(config, key, value_key):
            result.errors.append(
                RuleIssue(f"{field_name}.blocked", f"{current} is restricted", field_name)
            )
    allowed_regions = _values(config, "rules.allowed_regions", "region_codes")
    if allowed_regions and store_region.casefold() not in allowed_regions:
        result.errors.append(
            RuleIssue("region.restricted", "Store region is not allowed", "store_number")
        )
    allowed_groups = _values(config, "rules.allowed_buying_groups", "buying_group_codes")
    if allowed_groups and (buying_group or "").casefold() not in allowed_groups:
        result.errors.append(
            RuleIssue(
                "buying_group.restricted", "Store buying group is not allowed", "store_number"
            )
        )
    try:
        maximum_quantity = Decimal(
            str(config["rules.maximum_line_quantity"].get("quantity", 10000))
        )
    except (InvalidOperation, TypeError):
        result.errors.append(
            RuleIssue("configuration.invalid", "Maximum line quantity configuration is invalid")
        )
        maximum_quantity = Decimal("10000")
    blocked_products = _values(config, "rules.blocked_products", "product_codes")
    blocked_categories = _values(config, "rules.blocked_categories", "categories")
    blocked_brands = _values(config, "rules.blocked_brands", "brands")
    for line in request.line_items:
        product = getattr(line, "catalog_product", None)
        if line.quantity > maximum_quantity:
            result.errors.append(
                RuleIssue(
                    "quantity.maximum",
                    f"Line quantity cannot exceed {maximum_quantity}",
                    "line_items",
                )
            )
        if line.product_code.casefold() in blocked_products:
            result.errors.append(
                RuleIssue(
                    "product.blocked", f"Product {line.product_code} is restricted", "line_items"
                )
            )
        if product is not None and (product.category or "").casefold() in blocked_categories:
            result.errors.append(
                RuleIssue(
                    "category.blocked", f"Category {product.category} is restricted", "line_items"
                )
            )
        if product is not None and (product.brand or "").casefold() in blocked_brands:
            result.errors.append(
                RuleIssue("brand.blocked", f"Brand {product.brand} is restricted", "line_items")
            )
    return result
