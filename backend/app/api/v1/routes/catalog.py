from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.catalog import CatalogProduct, CatalogVendor
from app.models.identity import User
from app.schemas.catalog import (
    CatalogImportResponse,
    CatalogProductResponse,
    CatalogVendorCreate,
    CatalogVendorResponse,
    CatalogVendorUpdate,
    ModelCategoryResponse,
)
from app.services.catalog_import_service import (
    MAX_CATALOG_BYTES,
    CatalogImportError,
    import_catalog,
)
from app.services.model_category_service import list_model_categories

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/model-categories", response_model=list[ModelCategoryResponse])
def read_model_categories(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[ModelCategoryResponse]:
    return list_model_categories(db)


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
    user: User = Depends(get_current_user),
) -> list[CatalogVendor]:
    statement = select(CatalogVendor).order_by(CatalogVendor.vendor_code)
    if any(role.code == "VENDOR" for role in user.roles):
        if not user.vendor_code:
            return []
        statement = statement.where(CatalogVendor.vendor_code == user.vendor_code)
    if active_only:
        statement = statement.where(CatalogVendor.is_active.is_(True))
    return list(db.scalars(statement).all())


@router.post("/vendors", response_model=CatalogVendorResponse, status_code=201)
def create_vendor(
    payload: CatalogVendorCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("system.admin")),
) -> CatalogVendor:
    if db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == payload.vendor_code)):
        raise HTTPException(status_code=409, detail="Vendor code already exists")
    vendor = CatalogVendor(
        vendor_code=payload.vendor_code,
        name=payload.name.strip(),
        is_active=True,
        source_file="Admin entry",
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.patch("/vendors/{vendor_code}", response_model=CatalogVendorResponse)
def update_vendor(
    vendor_code: str,
    payload: CatalogVendorUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("system.admin")),
) -> CatalogVendor:
    vendor = db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == vendor_code))
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if payload.name is not None:
        vendor.name = payload.name.strip()
    if payload.is_active is not None:
        vendor.is_active = payload.is_active
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/products", response_model=list[CatalogProductResponse])
def list_products(
    search: str | None = None,
    vendor_code: str | None = None,
    active_only: bool = True,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CatalogProduct]:
    statement = (
        select(CatalogProduct)
        .where(CatalogProduct.model_number.is_not(None))
        .order_by(
            case(
                (CatalogProduct.is_clump.is_(True), 0),
                (CatalogProduct.part_of_clump.is_(False), 1),
                else_=2,
            ),
            CatalogProduct.model_number,
        )
        .limit(limit)
    )
    if active_only:
        statement = statement.where(
            CatalogProduct.is_active.is_(True), CatalogProduct.is_available.is_(True)
        )
    effective_vendor_code = vendor_code
    if any(role.code == "VENDOR" for role in user.roles):
        if not user.vendor_code:
            return []
        effective_vendor_code = user.vendor_code
    if effective_vendor_code:
        statement = statement.where(CatalogProduct.vendor_code == effective_vendor_code)
    if search:
        term = f"%{search}%"
        statement = statement.where(
            or_(
                CatalogProduct.product_code.ilike(term),
                CatalogProduct.name.ilike(term),
                CatalogProduct.model_number.ilike(term),
                CatalogProduct.department.ilike(term),
                CatalogProduct.product_category_code.ilike(term),
            )
        )
    return list(db.scalars(statement).all())
