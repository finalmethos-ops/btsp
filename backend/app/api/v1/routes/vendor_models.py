from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.catalog import (
    CatalogProductCostHistoryResponse,
    CatalogProductResponse,
    VendorModelImportResponse,
    VendorModelUpdate,
)
from app.services.catalog_import_service import MAX_CATALOG_BYTES
from app.services.vendor_model_service import (
    VendorModelError,
    export_vendor_models,
    import_vendor_models,
    list_cost_history,
    list_vendor_models,
    require_vendor_code,
    update_vendor_model,
)

router = APIRouter(prefix="/vendor-models", tags=["vendor-models"])


def _vendor_code(user: User) -> str:
    try:
        return require_vendor_code(user.vendor_code)
    except VendorModelError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[CatalogProductResponse])
def read_vendor_models(
    search: str | None = Query(default=None, max_length=160),
    classification: str = Query(default="all", pattern="^(all|clump|part_of_clump|single_item)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
) -> list[CatalogProductResponse]:
    return list_vendor_models(db, _vendor_code(user), search, classification)


@router.patch("/{product_code}", response_model=CatalogProductResponse)
def patch_vendor_model(
    product_code: str,
    payload: VendorModelUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
) -> CatalogProductResponse:
    try:
        product = update_vendor_model(db, _vendor_code(user), product_code, payload, user.email)
    except VendorModelError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return product


@router.get(
    "/{product_code}/cost-history",
    response_model=list[CatalogProductCostHistoryResponse],
)
def read_cost_history(
    product_code: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
) -> list[CatalogProductCostHistoryResponse]:
    history = list_cost_history(db, _vendor_code(user), product_code)
    if history is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return history


@router.get("/export/models.xlsx")
def download_vendor_models(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
) -> StreamingResponse:
    vendor_code = _vendor_code(user)
    content = export_vendor_models(db, vendor_code)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{vendor_code}-models.xlsx"',
        },
    )


@router.post("/import", response_model=VendorModelImportResponse)
async def upload_vendor_models(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.portal")),
) -> VendorModelImportResponse:
    filename = file.filename or "vendor-models.xlsx"
    try:
        created, updated, unchanged, total = import_vendor_models(
            db,
            _vendor_code(user),
            filename,
            await file.read(MAX_CATALOG_BYTES + 1),
            user.email,
        )
    except VendorModelError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return VendorModelImportResponse(
        filename=filename,
        created=created,
        updated=updated,
        unchanged=unchanged,
        total_rows=total,
    )
