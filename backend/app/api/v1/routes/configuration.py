from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.configuration_change import (
    ConfigurationChangeCreate,
    ConfigurationChangeDecision,
    ConfigurationChangeResponse,
)
from app.schemas.configuration_entry import ConfigEntryLookup, ConfigEntryResponse, ConfigEntryWrite
from app.services.configuration_seed_service import seed_default_configuration
from app.services.configuration_service import (
    decide_configuration_change,
    get_config_entry,
    list_config_entries,
    list_configuration_changes,
    request_configuration_change,
    upsert_config_entry,
)

router = APIRouter(prefix="/configuration", tags=["configuration"])


@router.get("", response_model=list[ConfigEntryResponse])
def read_config_entries(
    scope_type: str | None = None,
    scope_key: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("configuration.manage")),
) -> list[ConfigEntryResponse]:
    return list_config_entries(db, scope_type=scope_type, scope_key=scope_key)


@router.post("/lookup", response_model=ConfigEntryResponse)
def read_config_entry(
    payload: ConfigEntryLookup,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("configuration.manage")),
) -> ConfigEntryResponse:
    entry = get_config_entry(db, payload.scope_type, payload.scope_key, payload.key)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    return entry


@router.post("/seed-defaults")
def seed_config_defaults(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("configuration.manage")),
) -> dict[str, int]:
    return {"seeded_count": seed_default_configuration(db)}


@router.post("", response_model=ConfigEntryResponse)
def write_config_entry(
    payload: ConfigEntryWrite,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("configuration.manage")),
) -> ConfigEntryResponse:
    return upsert_config_entry(db, payload)


@router.get("/changes", response_model=list[ConfigurationChangeResponse])
def read_configuration_changes(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("configuration.manage")),
) -> list[ConfigurationChangeResponse]:
    return list_configuration_changes(db, status_filter)


@router.post(
    "/changes", response_model=ConfigurationChangeResponse, status_code=status.HTTP_201_CREATED
)
def create_configuration_change(
    payload: ConfigurationChangeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("configuration.manage")),
) -> ConfigurationChangeResponse:
    return request_configuration_change(db, payload, current_user.email)


@router.post("/changes/{change_id}/approve", response_model=ConfigurationChangeResponse)
def approve_configuration_change(
    change_id: str,
    payload: ConfigurationChangeDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("configuration.manage")),
) -> ConfigurationChangeResponse:
    try:
        change = decide_configuration_change(db, change_id, True, current_user.email, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if change is None:
        raise HTTPException(status_code=404, detail="Configuration change not found")
    return change


@router.post("/changes/{change_id}/reject", response_model=ConfigurationChangeResponse)
def reject_configuration_change(
    change_id: str,
    payload: ConfigurationChangeDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("configuration.manage")),
) -> ConfigurationChangeResponse:
    try:
        change = decide_configuration_change(db, change_id, False, current_user.email, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if change is None:
        raise HTTPException(status_code=404, detail="Configuration change not found")
    return change
