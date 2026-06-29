from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_any_permission, require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.approval_policy import ApprovalPolicyInput, ApprovalPolicyResult
from app.schemas.configuration_entry import ConfigEntryWrite
from app.services.approval_policy_defaults import BPP_APPROVAL_CONFIGURATION_DEFAULTS
from app.services.approval_policy_service import (
    ApprovalPolicyConfigurationError,
    evaluate_approval_policy,
    seed_bpp_approval_defaults,
)

router = APIRouter(prefix="/approval-policies", tags=["approval-policies"])


@router.post("/evaluate", response_model=ApprovalPolicyResult)
def evaluate_policy(
    payload: ApprovalPolicyInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_permission({"workflow.bpp.policy_read", "workflow.ind.review"})
    ),
) -> ApprovalPolicyResult:
    trusted_payload = payload.model_copy(update={"submitted_by": current_user.email})
    try:
        return evaluate_approval_policy(db, trusted_payload)
    except ApprovalPolicyConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.get("/bpp-purchasing/defaults", response_model=list[ConfigEntryWrite])
def read_bpp_approval_defaults(
    _current_user: User = Depends(require_permission("workflow.bpp.policy_read")),
) -> list[ConfigEntryWrite]:
    return [entry.model_copy(deep=True) for entry in BPP_APPROVAL_CONFIGURATION_DEFAULTS]


@router.post("/bpp-purchasing/seed-defaults")
def seed_bpp_policy_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workflow.bpp.policy_manage")),
) -> dict[str, int]:
    return {"seeded_count": seed_bpp_approval_defaults(db, actor=current_user.email)}
