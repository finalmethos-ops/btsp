from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.routes.purchase_orders import _allowed_workflows, _ensure_order_access
from app.schemas.purchase_order import PurchaseOrderGenerateRequest
from app.schemas.purchase_order_transmission import (
    PurchaseOrderTransmissionActionRequest,
    PurchaseOrderTransmissionCreate,
)


def _user_with_permissions(*permission_codes: str) -> SimpleNamespace:
    permissions = [SimpleNamespace(code=code) for code in permission_codes]
    return SimpleNamespace(roles=[SimpleNamespace(permissions=permissions)])


def test_purchase_order_scope_is_derived_from_management_permissions() -> None:
    bpp_user = _user_with_permissions("orders.bpp.manage")
    independent_user = _user_with_permissions("orders.independent.manage")
    combined_user = _user_with_permissions("orders.bpp.manage", "orders.independent.manage")

    assert _allowed_workflows(bpp_user) == {"BPP_PURCHASING"}  # type: ignore[arg-type]
    assert _allowed_workflows(independent_user) == {  # type: ignore[arg-type]
        "IND_PURCHASING"
    }
    assert _allowed_workflows(combined_user) == {  # type: ignore[arg-type]
        "BPP_PURCHASING",
        "IND_PURCHASING",
    }


def test_system_admin_has_unrestricted_purchase_order_scope() -> None:
    user = _user_with_permissions("system.admin")

    assert _allowed_workflows(user) == set()  # type: ignore[arg-type]
    _ensure_order_access(  # type: ignore[arg-type]
        user,
        SimpleNamespace(workflow_code="FUTURE_PURCHASING"),
    )


def test_purchase_order_scope_rejects_missing_and_cross_workflow_access() -> None:
    with pytest.raises(HTTPException) as missing:
        _allowed_workflows(_user_with_permissions())  # type: ignore[arg-type]
    assert missing.value.status_code == 403

    with pytest.raises(HTTPException) as cross_workflow:
        _ensure_order_access(  # type: ignore[arg-type]
            _user_with_permissions("orders.bpp.manage"),
            SimpleNamespace(workflow_code="IND_PURCHASING"),
        )
    assert cross_workflow.value.status_code == 403


@pytest.mark.parametrize("request_ids", [[], [str(index) for index in range(101)]])
def test_purchase_order_generation_enforces_batch_bounds(request_ids: list[str]) -> None:
    with pytest.raises(ValidationError):
        PurchaseOrderGenerateRequest(purchase_request_ids=request_ids)


def test_transmission_contract_rejects_unknown_values_and_oversized_text() -> None:
    with pytest.raises(ValidationError):
        PurchaseOrderTransmissionCreate(
            artifact_id="artifact-1",
            channel="external_email",  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        PurchaseOrderTransmissionCreate(
            artifact_id="artifact-1",
            channel="manual",
            destination="x" * 256,
        )
    with pytest.raises(ValidationError):
        PurchaseOrderTransmissionActionRequest(
            action="acknowledge",  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        PurchaseOrderTransmissionActionRequest(
            action="mark_failed",
            reason="x" * 1001,
        )
