from app.schemas.store_batch import StoreBatchRow
from app.services.store_batch_service import validate_store_row


def test_validate_store_row_requires_store_number() -> None:
    row = StoreBatchRow(store_number="", name="Test Store", region_code="SOUTHEAST")

    assert validate_store_row(row) == "Store number is required"


def test_validate_store_row_accepts_required_fields() -> None:
    row = StoreBatchRow(store_number="1001", name="Test Store", region_code="SOUTHEAST")

    assert validate_store_row(row) is None
