import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.api.v1.routes import catalog
from app.services.catalog_import_service import MAX_CATALOG_BYTES


class BoundedUpload:
    filename = "catalog.xlsx"

    def __init__(self) -> None:
        self.read_limit: int | None = None

    async def read(self, size: int = -1) -> bytes:
        self.read_limit = size
        return b"catalog-content"


def test_catalog_route_bounds_upload_read(monkeypatch: pytest.MonkeyPatch) -> None:
    upload = BoundedUpload()
    db = SimpleNamespace()
    now = datetime.now(UTC)
    run = SimpleNamespace(
        id=1,
        filename="catalog.xlsx",
        status="completed",
        vendor_rows=1,
        product_rows=1,
        errors=[],
        imported_by="admin@example.com",
        created_at=now,
        completed_at=now,
    )
    importer = MagicMock(return_value=run)
    monkeypatch.setattr(catalog, "import_catalog", importer)

    result = asyncio.run(
        catalog.upload_catalog(
            file=upload,  # type: ignore[arg-type]
            db=db,  # type: ignore[arg-type]
            current_user=SimpleNamespace(email="admin@example.com"),  # type: ignore[arg-type]
        )
    )

    assert upload.read_limit == MAX_CATALOG_BYTES + 1
    assert result.id == 1
    importer.assert_called_once_with(db, "catalog.xlsx", b"catalog-content", "admin@example.com")
