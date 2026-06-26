from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.store import Store
from app.schemas.store import StoreUpsert


def get_store_by_number(db: Session, store_number: str) -> Store | None:
    return db.scalar(select(Store).where(Store.store_number == store_number))


def list_active_stores(db: Session, region_code: str | None = None) -> list[Store]:
    statement = select(Store).where(Store.is_active.is_(True))
    if region_code is not None:
        statement = statement.where(Store.region_code == region_code)
    return list(db.scalars(statement).all())


def upsert_store(db: Session, payload: StoreUpsert) -> Store:
    store = get_store_by_number(db, payload.store_number)
    values = payload.model_dump()
    if store is None:
        store = Store(**values)
        db.add(store)
    else:
        for field, value in values.items():
            setattr(store, field, value)
    db.commit()
    db.refresh(store)
    return store


def check_region_scope(
    db: Session,
    user_region_code: str,
    target_store_numbers: list[str],
) -> list[str]:
    if not target_store_numbers:
        return []

    statement = select(Store.store_number).where(
        Store.store_number.in_(target_store_numbers),
        Store.region_code == user_region_code,
        Store.is_active.is_(True),
        Store.is_ordering_enabled.is_(True),
    )
    allowed_store_numbers = set(db.scalars(statement).all())
    return [store_number for store_number in target_store_numbers if store_number not in allowed_store_numbers]
