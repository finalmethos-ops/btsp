from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.reconciliation import (
    ReconciliationCreate,
    ReconciliationDecision,
    ReconciliationExceptionResolution,
    ReconciliationResponse,
)
from app.services.reconciliation_service import (
    ReconciliationError,
    create_reconciliation,
    decide_reconciliation,
    list_reconciliations,
    resolve_reconciliation_exception,
)

router = APIRouter(prefix="/reconciliations", tags=["reconciliation"])


@router.post("", response_model=ReconciliationResponse)
def post_reconciliation(
    payload: ReconciliationCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reconciliation.manage")),
) -> ReconciliationResponse:
    try:
        case, created = create_reconciliation(db, payload.invoice_id, user.email)
    except ReconciliationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return ReconciliationResponse.model_validate(case)


@router.get("", response_model=list[ReconciliationResponse])
def read_reconciliations(
    reconciliation_status: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("reconciliation.read")),
) -> list[ReconciliationResponse]:
    return [
        ReconciliationResponse.model_validate(item)
        for item in list_reconciliations(db, reconciliation_status)
    ]


@router.post("/exceptions/{exception_id}/resolution", response_model=ReconciliationResponse)
def resolve_exception(
    exception_id: str,
    payload: ReconciliationExceptionResolution,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reconciliation.manage")),
) -> ReconciliationResponse:
    try:
        case = resolve_reconciliation_exception(db, exception_id, payload, user.email)
    except ReconciliationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReconciliationResponse.model_validate(case)


@router.post("/{case_id}/decision", response_model=ReconciliationResponse)
def decide_case(
    case_id: str,
    payload: ReconciliationDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reconciliation.manage")),
) -> ReconciliationResponse:
    try:
        case = decide_reconciliation(db, case_id, payload, user.email)
    except ReconciliationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReconciliationResponse.model_validate(case)
