from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.identity import User
from app.schemas.store import RegionScopeCheck, RegionScopeResult, StoreResponse, StoreUpsert
from app.schemas.store_batch import StoreBatchRequest, StoreBatchResult
from app.services.store_batch_service import process_store_batch
from app.services.store_service import check_region_scope, get_store_by_number, list_active_stores, upsert_store

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=list[StoreResponse])
def read_stores(
    region_code: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[StoreResponse]:
    return list_active_stores(db, region_code=region_code)


@router.get("/{store_number}", response_model=StoreResponse)
def read_store(
    store_number: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> StoreResponse:
    store = get_store_by_number(db, store_number)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


@router.post("/upsert", response_model=StoreResponse)
def write_store(
    payload: StoreUpsert,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> StoreResponse:
    return upsert_store(db, payload)


@router.post("/batch", response_model=StoreBatchResult)
def write_store_batch(
    payload: StoreBatchRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> StoreBatchResult:
    return process_store_batch(db, payload)


@router.post("/scope-check", response_model=RegionScopeResult)
def read_region_scope(
    payload: RegionScopeCheck,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> RegionScopeResult:
    blocked = check_region_scope(db, payload.user_region_code, payload.target_store_numbers)
    return RegionScopeResult(allowed=not blocked, blocked_store_numbers=blocked)
