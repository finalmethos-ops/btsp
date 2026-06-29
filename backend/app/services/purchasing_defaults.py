from app.schemas.configuration_entry import ConfigEntryWrite

PURCHASING_RULE_DEFAULTS = {
    "rules.enabled": {"enabled": True},
    "rules.minimum_order_amount": {"amount": 0},
    "rules.maximum_line_quantity": {"quantity": 10000},
    "rules.blocked_stores": {"store_numbers": []},
    "rules.blocked_vendors": {"vendor_codes": []},
    "rules.blocked_products": {"product_codes": []},
    "rules.blocked_categories": {"categories": []},
    "rules.blocked_brands": {"brands": []},
    "rules.allowed_regions": {"region_codes": []},
    "rules.allowed_buying_groups": {"buying_group_codes": []},
    "rules.required_attachment_categories": {"categories": []},
    "draft.expiration_days": {"days": 30},
}


def purchasing_default_entries(actor: str) -> list[ConfigEntryWrite]:
    return [
        ConfigEntryWrite(
            scope_type="purchasing",
            scope_key=workflow_code,
            key=key,
            value=value,
            description=f"Purchasing domain default for {workflow_code}: {key}.",
            updated_by=actor,
        )
        for workflow_code in ("BPP_PURCHASING", "IND_PURCHASING")
        for key, value in PURCHASING_RULE_DEFAULTS.items()
    ]
