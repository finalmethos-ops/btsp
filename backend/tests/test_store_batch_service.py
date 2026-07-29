import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.store import Store
from app.schemas.store_batch import StoreBatchRequest, StoreBatchRow
from app.services.store_batch_service import (
    deactivate_stores_missing_from_batch,
    process_store_batch,
    validate_store_row,
)
from app.services.store_service import list_managed_stores, set_store_active


def test_validate_store_row_requires_store_number() -> None:
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        StoreBatchRow(store_number="", name="Test Store", region_code="SOUTHEAST")


def test_validate_store_row_accepts_required_fields() -> None:
    row = StoreBatchRow(store_number="1001", name="Test Store", region_code="SOUTHEAST")

    assert validate_store_row(row) is None


def test_authoritative_batch_deactivates_missing_stores() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                Store(store_number="0001", name="One", region_code="100"),
                Store(store_number="0999", name="Old", region_code="OLD"),
            ]
        )
        db.commit()
        payload = StoreBatchRequest(
            submitted_by="admin@example.com",
            rows=[StoreBatchRow(store_number="0001", name="One", region_code="100")],
        )

        assert deactivate_stores_missing_from_batch(db, payload) == 1
        old_store = db.scalar(select(Store).where(Store.store_number == "0999"))
        assert old_store is not None
        assert old_store.is_active is False
        assert old_store.is_ordering_enabled is False


def test_batch_row_number_is_not_persisted_as_store_field() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        result = process_store_batch(
            db,
            StoreBatchRequest(
                submitted_by="admin@example.com",
                rows=[
                    StoreBatchRow(
                        row_number=2,
                        store_number="0002",
                        name="Buddy's Store 0002",
                        region_code="9200",
                    )
                ],
            ),
        )

        assert result.upserted_rows == 1
        assert db.scalar(select(Store).where(Store.store_number == "0002")) is not None


def test_batch_without_timezone_preserves_existing_timezone() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            Store(
                store_number="0002",
                name="Existing Store",
                region_code="9200",
                timezone="America/Chicago",
            )
        )
        db.commit()

        process_store_batch(
            db,
            StoreBatchRequest(
                submitted_by="admin@example.com",
                rows=[
                    StoreBatchRow(
                        store_number="0002",
                        name="Updated Store",
                        region_code="9200",
                    )
                ],
            ),
        )

        store = db.scalar(select(Store).where(Store.store_number == "0002"))
        assert store is not None
        assert store.name == "Updated Store"
        assert store.timezone == "America/Chicago"


def test_store_disable_removes_store_from_active_management_list() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        store = Store(
            store_number="100",
            name="Managed Store",
            region_code="EAST",
            is_active=True,
            is_ordering_enabled=True,
        )
        db.add(store)
        db.commit()

        set_store_active(db, store, False)

        assert store.is_active is False
        assert store.is_ordering_enabled is False
        assert list_managed_stores(db, active=True) == []
        assert list_managed_stores(db, active=False) == [store]
