from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.catalog import CatalogVendor
from app.models.store import Store
from app.schemas.inventory import InventoryLedgerEntryCreate, InventoryTransferCreate
from app.services.inventory_service import InventoryError, position, post_entry, post_transfer


def test_inventory_position_and_transfer_are_ledger_backed() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(CatalogVendor(vendor_code="V-INV", name="Inventory Vendor", source_file="test"))
        db.add_all(
            [
                Store(store_number="001", name="One", region_code="EAST", is_active=True),
                Store(store_number="002", name="Two", region_code="EAST", is_active=True),
            ]
        )
        db.commit()
        post_entry(
            db,
            InventoryLedgerEntryCreate(
                product_code="SKU-1",
                store_number="001",
                quantity_delta=10,
                reason="receipt",
            ),
            "ops@example.com",
        )
        transfer = post_transfer(
            db,
            InventoryTransferCreate(
                product_code="SKU-1",
                from_store_number="001",
                to_store_number="002",
                quantity=4,
            ),
            "ops@example.com",
        )
        assert transfer.status == "posted"
        assert position(db, "SKU-1", "001")[0] == 6
        assert position(db, "SKU-1", "002")[0] == 4


def test_transfer_cannot_exceed_available_inventory() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                Store(store_number="001", name="One", region_code="EAST", is_active=True),
                Store(store_number="002", name="Two", region_code="EAST", is_active=True),
            ]
        )
        db.commit()
        try:
            post_transfer(
                db,
                InventoryTransferCreate(
                    product_code="SKU-1",
                    from_store_number="001",
                    to_store_number="002",
                    quantity=1,
                ),
                "ops@example.com",
            )
        except InventoryError:
            pass
        else:
            raise AssertionError("Expected transfer to reject insufficient inventory")
