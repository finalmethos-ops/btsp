from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_any_permission, require_permission
from app.db.session import get_db
from app.models.identity import User
from app.models.store import EntityRegion
from app.schemas.store import (
    EntityRegionResponse,
    EntityRegionWrite,
    POStoreFilterEntity,
    POStoreFilterOptions,
    RegionScopeCheck,
    RegionScopeResult,
    StoreDirectoryOptions,
    StoreResponse,
    StoreUpsert,
)
from app.schemas.store_batch import StoreBatchRequest, StoreBatchResult
from app.services.store_batch_service import (
    deactivate_stores_missing_from_batch,
    process_store_batch,
)
from app.services.store_service import (
    check_region_scope,
    get_store_by_number,
    list_active_stores,
    list_managed_stores,
    list_store_directory_options,
    set_store_active,
    upsert_store,
)
from app.services.store_workbook_import import StoreWorkbookError, parse_store_workbook
from app.services.vendor_geography_service import eligible_stores

router = APIRouter(prefix="/stores", tags=["stores"])
MAX_STORE_WORKBOOK_BYTES = 10 * 1024 * 1024


@router.get("/entity-regions", response_model=list[EntityRegionResponse])
def read_entity_regions(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("system.admin")),
) -> list[EntityRegion]:
    return list(
        db.scalars(
            select(EntityRegion).order_by(EntityRegion.entity_code, EntityRegion.region_code)
        )
    )


@router.post("/entity-regions", response_model=EntityRegionResponse, status_code=201)
def write_entity_region(
    payload: EntityRegionWrite,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("system.admin")),
) -> EntityRegion:
    entity_code = payload.entity_code.strip().upper()
    region_code = payload.region_code.strip().upper()
    item = db.get(EntityRegion, {"entity_code": entity_code, "region_code": region_code})
    if item is None:
        item = EntityRegion(entity_code=entity_code, region_code=region_code)
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


@router.delete("/entity-regions/{entity_code}/{region_code}", status_code=204)
def delete_entity_region(
    entity_code: str,
    region_code: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("system.admin")),
) -> None:
    item = db.get(
        EntityRegion, {"entity_code": entity_code.upper(), "region_code": region_code.upper()}
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Entity region not found")
    db.delete(item)
    db.commit()


@router.get("/eligible", response_model=list[StoreResponse])
def read_eligible_stores(
    vendor_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StoreResponse]:
    if any(role.code == "VENDOR" for role in current_user.roles) and (
        not current_user.vendor_code or current_user.vendor_code != vendor_code
    ):
        raise HTTPException(status_code=403, detail="Vendor identity mismatch")
    return eligible_stores(db, vendor_code)


@router.get("", response_model=list[StoreResponse])
def read_stores(
    region_code: str | None = None,
    entity_code: str | None = None,
    purchasing_program: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("stores.manage")),
) -> list[StoreResponse]:
    return list_active_stores(
        db,
        region_code=region_code,
        entity_code=entity_code,
        purchasing_program=purchasing_program,
    )


@router.get("/directory-options", response_model=StoreDirectoryOptions)
def read_store_directory_options(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_any_permission({"stores.read", "stores.manage"})),
) -> StoreDirectoryOptions:
    return StoreDirectoryOptions(**list_store_directory_options(db))


@router.get("/po-filter-options", response_model=POStoreFilterOptions)
def read_po_filter_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_permission(
            {
                "vendor.portal",
                "purchase_orders.handoff",
                "reconciliation.read",
                "system.admin",
            }
        )
    ),
) -> POStoreFilterOptions:
    if any(role.code == "VENDOR" for role in current_user.roles):
        stores = eligible_stores(db, current_user.vendor_code) if current_user.vendor_code else []
    else:
        stores = list_active_stores(db)
    regions_by_entity: dict[str, set[str]] = {}
    for store in stores:
        if not store.entity_code or not store.region_code:
            continue
        regions_by_entity.setdefault(store.entity_code, set()).add(store.region_code)
    return POStoreFilterOptions(
        entities=[
            POStoreFilterEntity(
                entity_code=entity_code,
                regions=sorted(regions),
            )
            for entity_code, regions in sorted(regions_by_entity.items())
        ]
    )


@router.get("/management", response_model=list[StoreResponse])
def read_managed_stores(
    active: bool | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_any_permission({"stores.read", "stores.manage"})),
) -> list[StoreResponse]:
    return list_managed_stores(db, active)


@router.post("/import-workbook", response_model=StoreBatchResult)
async def import_store_workbook(
    workbook: UploadFile = File(...),
    authoritative: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("stores.manage")),
) -> StoreBatchResult:
    try:
        content = await workbook.read(MAX_STORE_WORKBOOK_BYTES + 1)
        if len(content) > MAX_STORE_WORKBOOK_BYTES:
            raise StoreWorkbookError(
                f"Store workbook must not exceed {MAX_STORE_WORKBOOK_BYTES} bytes"
            )
        payload = parse_store_workbook(content, current_user.email)
    except StoreWorkbookError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    result = process_store_batch(db, payload)
    if authoritative and not result.failed_rows:
        deactivate_stores_missing_from_batch(db, payload)
    return result


@router.get("/{store_number}", response_model=StoreResponse)
def read_store(
    store_number: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("stores.manage")),
) -> StoreResponse:
    store = get_store_by_number(db, store_number)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


@router.patch("/{store_number}/status", response_model=StoreResponse)
def change_store_status(
    store_number: str,
    is_active: bool,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("stores.manage")),
) -> StoreResponse:
    store = get_store_by_number(db, store_number)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return set_store_active(db, store, is_active)


@router.post("/upsert", response_model=StoreResponse)
def write_store(
    payload: StoreUpsert,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("stores.manage")),
) -> StoreResponse:
    return upsert_store(db, payload)


@router.post("/batch", response_model=StoreBatchResult)
def write_store_batch(
    payload: StoreBatchRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("stores.manage")),
) -> StoreBatchResult:
    return process_store_batch(db, payload)


@router.post("/scope-check", response_model=RegionScopeResult)
def read_region_scope(
    payload: RegionScopeCheck,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("stores.manage")),
) -> RegionScopeResult:
    blocked = check_region_scope(db, payload.user_region_code, payload.target_store_numbers)
    return RegionScopeResult(allowed=not blocked, blocked_store_numbers=blocked)
