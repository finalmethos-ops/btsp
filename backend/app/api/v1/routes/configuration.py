from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.identity import User
from app.schemas.configuration_entry import ConfigEntryLookup, ConfigEntryResponse, ConfigEntryWrite
from app.services.configuration_service import get_config_entry, list_config_entries, upsert_config_entry

router = APIRouter(prefix="/configuration", tags=["configuration"])


@router.get("", response_model=list[ConfigEntryResponse])
def read_config_entries(
    scope_type: str | None = None,
    scope_key: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[ConfigEntryResponse]:
    return list_config_entries(db, scope_type=scope_type, scope_key=scope_key)


@router.post("/lookup", response_model=ConfigEntryResponse)
def read_config_entry(
    payload: ConfigEntryLookup,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ConfigEntryResponse:
    entry = get_config_entry(db, payload.scope_type, payload.scope_key, payload.key)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    return entry


@router.post("", response_model=ConfigEntryResponse)
def write_config_entry(
    payload: ConfigEntryWrite,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ConfigEntryResponse:
    return upsert_config_entry(db, payload)
