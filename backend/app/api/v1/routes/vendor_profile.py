from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.catalog import CatalogVendor
from app.models.identity import User
from app.schemas.catalog import (
    VendorMOQCombinationWrite,
    VendorMOQRuleResponse,
    VendorMOQRuleWrite,
    VendorStateExclusions,
)
from app.schemas.order_lifecycle import VendorEmailPreference
from app.services.vendor_geography_service import (
    VendorGeographyError,
    get_excluded_states,
    set_excluded_states,
)
from app.services.vendor_model_service import require_vendor_code
from app.services.vendor_moq_service import (
    VendorMOQError,
    contributor_ids,
    create_rule,
    list_rules,
    set_contributors,
    update_rule,
)

router = APIRouter(prefix="/vendor-profile", tags=["vendor-profile"])


def _code(user: User) -> str:
    try:
        return require_vendor_code(user.vendor_code)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _response(db: Session, rule) -> VendorMOQRuleResponse:
    return VendorMOQRuleResponse.model_validate(rule, from_attributes=True).model_copy(
        update={"contributor_rule_ids": contributor_ids(db, rule.id)}
    )


@router.get("/moq-rules", response_model=list[VendorMOQRuleResponse])
def get_rules(
    db: Session = Depends(get_db), user: User = Depends(require_permission("vendor.portal"))
):
    return [_response(db, rule) for rule in list_rules(db, _code(user))]


@router.post("/moq-rules", response_model=VendorMOQRuleResponse, status_code=201)
def post_rule(
    payload: VendorMOQRuleWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        return _response(db, create_rule(db, _code(user), payload))
    except VendorMOQError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/moq-rules/{rule_id}", response_model=VendorMOQRuleResponse)
def put_rule(
    rule_id: int,
    payload: VendorMOQRuleWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        rule = update_rule(db, _code(user), rule_id, payload)
    except VendorMOQError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if rule is None:
        raise HTTPException(status_code=404, detail="MOQ rule not found")
    return _response(db, rule)


@router.put("/moq-rules/{rule_id}/contributors", status_code=status.HTTP_204_NO_CONTENT)
def put_contributors(
    rule_id: int,
    payload: VendorMOQCombinationWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        set_contributors(db, _code(user), rule_id, payload.contributor_rule_ids)
    except VendorMOQError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/state-exclusions", response_model=VendorStateExclusions)
def get_state_exclusions(
    db: Session = Depends(get_db), user: User = Depends(require_permission("vendor.portal"))
):
    return VendorStateExclusions(state_codes=get_excluded_states(db, _code(user)))


@router.put("/state-exclusions", response_model=VendorStateExclusions)
def put_state_exclusions(
    payload: VendorStateExclusions,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    try:
        codes = set_excluded_states(db, _code(user), payload.state_codes)
    except VendorGeographyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return VendorStateExclusions(state_codes=codes)


@router.get("/po-email-preference", response_model=VendorEmailPreference)
def get_po_email_preference(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    vendor = db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == _code(user)))
    return VendorEmailPreference(po_email_recipient=vendor.po_email_recipient if vendor else None)


@router.put("/po-email-preference", response_model=VendorEmailPreference)
def put_po_email_preference(
    payload: VendorEmailPreference,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
):
    vendor = db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == _code(user)))
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
    vendor.po_email_recipient = payload.po_email_recipient
    db.commit()
    return payload
