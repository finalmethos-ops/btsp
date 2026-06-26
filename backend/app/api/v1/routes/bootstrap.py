from hmac import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.admin_bootstrap import AdminBootstrapRequest, AdminBootstrapResponse
from app.services.admin_bootstrap_service import bootstrap_admin_user

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])


@router.post("/admin", response_model=AdminBootstrapResponse)
def create_bootstrap_admin(
    payload: AdminBootstrapRequest,
    db: Session = Depends(get_db),
    bootstrap_token: str | None = Header(default=None, alias="X-BTSP-Bootstrap-Token"),
) -> AdminBootstrapResponse:
    if not bootstrap_token or not compare_digest(bootstrap_token, settings.bootstrap_admin_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bootstrap token")
    return bootstrap_admin_user(db, payload)
