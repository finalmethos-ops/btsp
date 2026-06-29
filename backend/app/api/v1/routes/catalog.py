from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.catalog import CatalogProduct, CatalogVendor
from app.models.identity import User
from app.schemas.catalog import CatalogImportResponse, CatalogProductResponse, CatalogVendorResponse
from app.services.catalog_import_service import (
    MAX_CATALOG_BYTES,
    CatalogImportError,
    import_catalog,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post("/imports", response_model=CatalogImportResponse)
async def upload_catalog(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("configuration.manage")),
) -> CatalogImportResponse:
    try:
        run = import_catalog(
            db,
            file.filename or "catalog.xlsx",
            await file.read(MAX_CATALOG_BYTES + 1),
            current_user.email,
        )
    except CatalogImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CatalogImportResponse.model_validate(run, from_attributes=True)


@router.get("/vendors", response_model=list[CatalogVendorResponse])
def list_vendors(
    active_only: bool = True,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[CatalogVendor]:
    statement = select(CatalogVendor).order_by(CatalogVendor.vendor_code)
    if active_only:
        statement = statement.where(CatalogVendor.is_active.is_(True))
    return list(db.scalars(statement).all())


@router.get("/products", response_model=list[CatalogProductResponse])
def list_products(
    search: str | None = None,
    vendor_code: str | None = None,
    active_only: bool = True,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[CatalogProduct]:
    statement = select(CatalogProduct).order_by(CatalogProduct.product_code).limit(limit)
    if active_only:
        statement = statement.where(
            CatalogProduct.is_active.is_(True), CatalogProduct.is_available.is_(True)
        )
    if vendor_code:
        statement = statement.where(CatalogProduct.vendor_code == vendor_code)
    if search:
        term = f"%{search}%"
        statement = statement.where(
            or_(
                CatalogProduct.product_code.ilike(term),
                CatalogProduct.name.ilike(term),
                CatalogProduct.model_number.ilike(term),
            )
        )
    return list(db.scalars(statement).all())
