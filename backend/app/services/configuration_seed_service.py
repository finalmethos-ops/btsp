from sqlalchemy.orm import Session

from app.services.configuration_defaults import DEFAULT_CONFIGURATION_ENTRIES
from app.services.configuration_service import upsert_config_entry


def seed_default_configuration(db: Session) -> int:
    seeded_count = 0
    for entry in DEFAULT_CONFIGURATION_ENTRIES:
        upsert_config_entry(db, entry)
        seeded_count += 1
    return seeded_count
