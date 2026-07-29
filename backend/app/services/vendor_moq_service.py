from decimal import Decimal

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.catalog import CatalogProduct, VendorMOQCombination, VendorMOQRule
from app.models.purchasing import PurchaseRequest
from app.schemas.catalog import VendorMOQRuleWrite
from app.services.purchasing_rule_service import RuleIssue


class VendorMOQError(ValueError):
    pass


def sole_active_rule(db: Session, vendor_code: str) -> VendorMOQRule | None:
    rules = list(
        db.scalars(
            select(VendorMOQRule).where(
                VendorMOQRule.vendor_code == vendor_code,
                VendorMOQRule.is_active.is_(True),
            )
        ).all()
    )
    return rules[0] if len(rules) == 1 else None


def apply_sole_rule_to_models(db: Session, vendor_code: str) -> int:
    rule = sole_active_rule(db, vendor_code)
    if rule is None:
        return 0
    result = db.execute(
        update(CatalogProduct)
        .where(
            CatalogProduct.vendor_code == vendor_code,
            CatalogProduct.moq_rule_id != rule.id,
        )
        .values(moq_rule_id=rule.id)
    )
    unassigned = db.execute(
        update(CatalogProduct)
        .where(
            CatalogProduct.vendor_code == vendor_code,
            CatalogProduct.moq_rule_id.is_(None),
        )
        .values(moq_rule_id=rule.id)
    )
    return int(result.rowcount or 0) + int(unassigned.rowcount or 0)


def list_rules(db: Session, vendor_code: str) -> list[VendorMOQRule]:
    return list(
        db.scalars(
            select(VendorMOQRule)
            .where(VendorMOQRule.vendor_code == vendor_code)
            .order_by(VendorMOQRule.name)
        ).all()
    )


def contributor_ids(db: Session, rule_id: int) -> list[int]:
    return list(
        db.scalars(
            select(VendorMOQCombination.source_rule_id).where(
                VendorMOQCombination.target_rule_id == rule_id
            )
        ).all()
    )


def create_rule(db: Session, vendor_code: str, payload: VendorMOQRuleWrite) -> VendorMOQRule:
    existing = db.scalar(
        select(VendorMOQRule.id).where(
            VendorMOQRule.vendor_code == vendor_code,
            func.lower(VendorMOQRule.code) == payload.code.lower(),
        )
    )
    if existing is not None:
        raise VendorMOQError("MOQ code already exists for this vendor")
    if (
        payload.threshold_type == "unit_quantity"
        and payload.threshold_value != payload.threshold_value.to_integral_value()
    ):
        raise VendorMOQError("Unit quantity MOQ must be a whole number")
    rule = VendorMOQRule(vendor_code=vendor_code, **payload.model_dump())
    db.add(rule)
    db.flush()
    apply_sole_rule_to_models(db, vendor_code)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(
    db: Session, vendor_code: str, rule_id: int, payload: VendorMOQRuleWrite
) -> VendorMOQRule | None:
    rule = db.scalar(
        select(VendorMOQRule).where(
            VendorMOQRule.id == rule_id, VendorMOQRule.vendor_code == vendor_code
        )
    )
    if rule is None:
        return None
    duplicate = db.scalar(
        select(VendorMOQRule.id).where(
            VendorMOQRule.vendor_code == vendor_code,
            func.lower(VendorMOQRule.code) == payload.code.lower(),
            VendorMOQRule.id != rule_id,
        )
    )
    if duplicate is not None:
        raise VendorMOQError("MOQ code already exists for this vendor")
    if (
        payload.threshold_type == "unit_quantity"
        and payload.threshold_value != payload.threshold_value.to_integral_value()
    ):
        raise VendorMOQError("Unit quantity MOQ must be a whole number")
    for key, value in payload.model_dump().items():
        setattr(rule, key, value)
    db.flush()
    apply_sole_rule_to_models(db, vendor_code)
    db.commit()
    db.refresh(rule)
    return rule


def set_contributors(db: Session, vendor_code: str, target_id: int, source_ids: list[int]) -> bool:
    rules = list(
        db.scalars(
            select(VendorMOQRule).where(
                VendorMOQRule.vendor_code == vendor_code,
                VendorMOQRule.id.in_({target_id, *source_ids}),
            )
        ).all()
    )
    if len({r.id for r in rules}) != len({target_id, *source_ids}) or target_id in source_ids:
        raise VendorMOQError("MOQ combinations must reference distinct rules for this vendor")
    db.execute(delete(VendorMOQCombination).where(VendorMOQCombination.target_rule_id == target_id))
    db.add_all(
        VendorMOQCombination(source_rule_id=value, target_rule_id=target_id)
        for value in set(source_ids)
    )
    db.commit()
    return True


def evaluate_vendor_moq(db: Session, request: PurchaseRequest) -> list[RuleIssue]:
    rules = {rule.id: rule for rule in list_rules(db, request.vendor_code) if rule.is_active}
    automatic_rule = next(iter(rules)) if len(rules) == 1 else None
    grouped: dict[int, list] = {}
    for line in request.line_items:
        rule_id = line.catalog_product.moq_rule_id if line.catalog_product else None
        if automatic_rule is not None:
            rule_id = automatic_rule
        if rule_id in rules:
            grouped.setdefault(rule_id, []).append(line)
    issues: list[RuleIssue] = []
    for target_id in grouped:
        rule = rules[target_id]
        sources = set(contributor_ids(db, target_id)) | {target_id}
        lines = [line for source in sources for line in grouped.get(source, [])]
        actual = (
            sum((line.quantity for line in lines), Decimal("0"))
            if rule.threshold_type == "unit_quantity"
            else sum((line.quantity * line.unit_price for line in lines), Decimal("0"))
        )
        if actual < rule.threshold_value:
            unit = "units" if rule.threshold_type == "unit_quantity" else "currency value"
            issues.append(
                RuleIssue(
                    "vendor_moq.minimum",
                    f"{rule.name} requires {rule.threshold_value} {unit}; "
                    f"current qualifying total is {actual}",
                    "line_items",
                )
            )
    return issues
