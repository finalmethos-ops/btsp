from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.catalog import CatalogVendor
from app.models.store import Store
from app.services.vendor_geography_service import (
    eligible_stores,
    set_excluded_states,
    state_is_excluded,
)


def test_vendor_state_exclusions_filter_eligible_stores() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            CatalogVendor(
                vendor_code="V-GEO",
                name="Geography Vendor",
                is_active=True,
                source_file="test.xlsx",
            )
        )
        db.add_all(
            [
                Store(store_number="001", name="Florida", region_code="S", state_code="FL"),
                Store(store_number="002", name="Georgia", region_code="S", state_code="GA"),
            ]
        )
        db.commit()

        assert set_excluded_states(db, "V-GEO", ["fl"]) == ["FL"]
        assert state_is_excluded(db, "V-GEO", "FL") is True
        assert [store.store_number for store in eligible_stores(db, "V-GEO")] == ["002"]
