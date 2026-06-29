from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import CatalogImportRun, CatalogProduct, CatalogVendor
from app.schemas.event_snapshot import EventSnapshotCreate
from app.services.snapshot_service import append_snapshot

MAX_CATALOG_BYTES = 10 * 1024 * 1024
VENDOR_REQUIRED = {"vendor_code", "name"}
PRODUCT_REQUIRED = {"product_code", "vendor_code", "name", "unit_price"}


class CatalogImportError(ValueError):
    pass


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _boolean(value: Any, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "y", "1"}:
        return True
    if normalized in {"false", "no", "n", "0"}:
        return False
    raise CatalogImportError(f"Invalid boolean value: {value}")


def _decimal(value: Any, field: str, minimum: Decimal = Decimal("0")) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise CatalogImportError(f"{field} must be numeric") from exc
    if parsed < minimum:
        raise CatalogImportError(f"{field} must be at least {minimum}")
    return parsed


def _sheet_rows(workbook: Any, name: str, required: set[str]) -> list[dict[str, Any]]:
    if name not in workbook.sheetnames:
        raise CatalogImportError(f"Workbook is missing required sheet: {name}")
    rows = workbook[name].iter_rows(values_only=True)
    try:
        raw_headers = next(rows)
    except StopIteration as exc:
        raise CatalogImportError(f"Sheet {name} is empty") from exc
    headers = [_text(value).lower() for value in raw_headers]
    missing = required - set(headers)
    if missing:
        raise CatalogImportError(f"Sheet {name} is missing columns: {', '.join(sorted(missing))}")
    return [
        dict(zip(headers, row, strict=False))
        for row in rows
        if any(value is not None for value in row)
    ]


def _parse(content: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise CatalogImportError("File is not a readable Excel workbook") from exc
    vendors = _sheet_rows(workbook, "Vendors", VENDOR_REQUIRED)
    products = _sheet_rows(workbook, "Products", PRODUCT_REQUIRED)
    parsed_vendors: list[dict[str, Any]] = []
    vendor_codes: set[str] = set()
    for number, row in enumerate(vendors, start=2):
        code = _text(row.get("vendor_code"))
        name = _text(row.get("name"))
        if not code or not name:
            raise CatalogImportError(f"Vendors row {number}: vendor_code and name are required")
        if code in vendor_codes:
            raise CatalogImportError(f"Vendors row {number}: duplicate vendor_code {code}")
        vendor_codes.add(code)
        parsed_vendors.append(
            {"vendor_code": code, "name": name, "is_active": _boolean(row.get("is_active"))}
        )
    parsed_products: list[dict[str, Any]] = []
    product_codes: set[str] = set()
    for number, row in enumerate(products, start=2):
        code = _text(row.get("product_code"))
        vendor_code = _text(row.get("vendor_code"))
        name = _text(row.get("name"))
        if not code or not vendor_code or not name:
            raise CatalogImportError(
                f"Products row {number}: product_code, vendor_code, and name are required"
            )
        if code in product_codes:
            raise CatalogImportError(f"Products row {number}: duplicate product_code {code}")
        if vendor_code not in vendor_codes:
            raise CatalogImportError(f"Products row {number}: unknown vendor_code {vendor_code}")
        product_codes.add(code)
        parsed_products.append(
            {
                "product_code": code,
                "vendor_code": vendor_code,
                "name": name,
                "model_number": _text(row.get("model_number")) or None,
                "category": _text(row.get("category")) or None,
                "brand": _text(row.get("brand")) or None,
                "unit_price": _decimal(row.get("unit_price"), "unit_price"),
                "currency": (_text(row.get("currency")) or "USD").upper(),
                "minimum_order_quantity": _decimal(
                    row.get("minimum_order_quantity") or 1,
                    "minimum_order_quantity",
                    Decimal("0.0001"),
                ),
                "is_available": _boolean(row.get("is_available")),
                "is_active": _boolean(row.get("is_active")),
            }
        )
    return parsed_vendors, parsed_products


def import_catalog(db: Session, filename: str, content: bytes, actor: str) -> CatalogImportRun:
    if not filename.lower().endswith(".xlsx"):
        raise CatalogImportError("Catalog file must use the .xlsx format")
    if not content or len(content) > MAX_CATALOG_BYTES:
        raise CatalogImportError("Catalog file must be non-empty and no larger than 10 MB")
    vendors, products = _parse(content)
    run = CatalogImportRun(filename=filename, status="processing", imported_by=actor)
    db.add(run)
    for values in vendors:
        item = db.scalar(
            select(CatalogVendor).where(CatalogVendor.vendor_code == values["vendor_code"])
        )
        if item is None:
            item = CatalogVendor(**values, source_file=filename)
            db.add(item)
        else:
            for key, value in values.items():
                setattr(item, key, value)
            item.source_file = filename
    db.flush()
    for values in products:
        item = db.scalar(
            select(CatalogProduct).where(CatalogProduct.product_code == values["product_code"])
        )
        if item is None:
            item = CatalogProduct(**values, source_file=filename)
            db.add(item)
        else:
            for key, value in values.items():
                setattr(item, key, value)
            item.source_file = filename
    run.status = "completed"
    run.vendor_rows = len(vendors)
    run.product_rows = len(products)
    run.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(run)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="catalog.imported",
            entity_type="catalog_import",
            entity_id=str(run.id),
            actor=actor,
            payload={
                "filename": filename,
                "vendor_rows": len(vendors),
                "product_rows": len(products),
            },
        ),
    )
    return run
