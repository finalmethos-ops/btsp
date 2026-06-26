from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.configuration import ConfigurationEntry
from app.schemas.configuration_entry import ConfigEntryWrite
from app.schemas.event_snapshot import EventSnapshotCreate
from app.services.snapshot_service import append_snapshot


def get_config_entry(
    db: Session,
    scope_type: str,
    scope_key: str,
    key: str,
) -> ConfigurationEntry | None:
    statement = select(ConfigurationEntry).where(
        ConfigurationEntry.scope_type == scope_type,
        ConfigurationEntry.scope_key == scope_key,
        ConfigurationEntry.key == key,
        ConfigurationEntry.is_active.is_(True),
    )
    return db.scalar(statement)


def list_config_entries(
    db: Session,
    scope_type: str | None = None,
    scope_key: str | None = None,
) -> list[ConfigurationEntry]:
    statement = select(ConfigurationEntry).where(ConfigurationEntry.is_active.is_(True))
    if scope_type is not None:
        statement = statement.where(ConfigurationEntry.scope_type == scope_type)
    if scope_key is not None:
        statement = statement.where(ConfigurationEntry.scope_key == scope_key)
    return list(db.scalars(statement).all())


def upsert_config_entry(db: Session, payload: ConfigEntryWrite) -> ConfigurationEntry:
    entry = get_config_entry(db, payload.scope_type, payload.scope_key, payload.key)
    before_value = None if entry is None else entry.value
    values = payload.model_dump()
    if entry is None:
        entry = ConfigurationEntry(**values)
        db.add(entry)
    else:
        for field, value in values.items():
            setattr(entry, field, value)
    db.commit()
    db.refresh(entry)

    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="configuration.changed",
            entity_type="configuration_entry",
            entity_id=f"{entry.scope_type}:{entry.scope_key}:{entry.key}",
            actor=entry.updated_by,
            payload={
                "scope_type": entry.scope_type,
                "scope_key": entry.scope_key,
                "key": entry.key,
                "before": before_value,
                "after": entry.value,
            },
        ),
    )
    return entry
