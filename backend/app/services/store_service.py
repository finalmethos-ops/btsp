from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.store import Store
from app.schemas.store import StoreUpsert


def get_store_by_number(db: Session, store_number: str) -> Store | None:
    return db.scalar(select(Store).where(Store.store_number == store_number))


def list_active_stores(
    db: Session,
    region_code: str | None = None,
    entity_code: str | None = None,
    purchasing_program: str | None = None,
) -> list[Store]:
    statement = select(Store).where(Store.is_active.is_(True))
    if region_code is not None:
        statement = statement.where(Store.region_code == region_code)
    if entity_code is not None:
        statement = statement.where(Store.entity_code == entity_code)
    if purchasing_program is not None:
        statement = statement.where(Store.purchasing_program == purchasing_program)
    return list(db.scalars(statement.order_by(Store.store_number)).all())


def list_managed_stores(db: Session, active: bool | None = None) -> list[Store]:
    statement = select(Store)
    if active is not None:
        statement = statement.where(Store.is_active.is_(active))
    return list(db.scalars(statement.order_by(Store.store_number)).all())


def list_store_directory_options(db: Session) -> dict[str, object]:
    def values(field: object) -> list[str]:
        statement = select(field).where(field.is_not(None)).distinct().order_by(field)  # type: ignore[attr-defined]
        return [value for value in db.scalars(statement).all() if value]

    entity_regions: dict[str, list[str]] = {}
    for entity_code, region_code in db.execute(
        select(Store.entity_code, Store.region_code)
        .where(
            Store.is_active.is_(True),
            Store.entity_code.is_not(None),
            Store.region_code.is_not(None),
        )
        .distinct()
        .order_by(Store.entity_code, Store.region_code)
    ):
        if entity_code and region_code:
            entity_regions.setdefault(entity_code, []).append(region_code)
    return {
        "entities": values(Store.entity_code),
        "purchasing_programs": values(Store.purchasing_program),
        "regions": values(Store.region_code),
        "entity_regions": entity_regions,
    }


def upsert_store(db: Session, payload: StoreUpsert) -> Store:
    store = get_store_by_number(db, payload.store_number)
    values = payload.model_dump(exclude={"row_number"}, exclude_unset=True)
    if store is None:
        store = Store(**values)
        db.add(store)
    else:
        for field, value in values.items():
            setattr(store, field, value)
    db.commit()
    db.refresh(store)
    return store


def set_store_active(db: Session, store: Store, is_active: bool) -> Store:
    store.is_active = is_active
    # An inactive store must never remain available to purchasing workflows.
    store.is_ordering_enabled = is_active
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
    return [
        store_number
        for store_number in target_store_numbers
        if store_number not in allowed_store_numbers
    ]
