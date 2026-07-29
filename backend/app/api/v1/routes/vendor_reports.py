from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.vendor_report import VendorReportResponse
from app.services.vendor_model_service import require_vendor_code
from app.services.vendor_report_service import build_vendor_report

router = APIRouter(prefix="/vendor-reports", tags=["vendor-reports"])


@router.get("", response_model=VendorReportResponse)
def vendor_report(
    year: int | None = Query(default=None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
) -> VendorReportResponse:
    try:
        vendor_code = require_vendor_code(user.vendor_code)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return build_vendor_report(db, vendor_code, year)
