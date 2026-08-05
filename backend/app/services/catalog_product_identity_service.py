import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import CatalogProduct


def allocate_product_code(db: Session, vendor_code: str, model_number: str) -> str:
    """Allocate the globally unique internal key for a vendor-owned model."""
    existing = db.scalar(
        select(CatalogProduct.product_code).where(
            CatalogProduct.vendor_code == vendor_code,
            CatalogProduct.model_number == model_number,
        )
    )
    if existing is not None:
        return existing

    if (
        db.scalar(select(CatalogProduct.id).where(CatalogProduct.product_code == model_number))
        is None
    ):
        # Preserve familiar legacy keys when no cross-vendor collision exists.
        return model_number

    vendor_stem = re.sub(r"[^A-Z0-9]+", "-", vendor_code.upper()).strip("-") or "VENDOR"
    model_stem = re.sub(r"[^A-Z0-9]+", "-", model_number.upper()).strip("-") or "MODEL"
    digest = hashlib.sha256(f"{vendor_code}\0{model_number}".encode()).hexdigest()[:10].upper()
    suffix = f"-{digest}"
    base = f"{vendor_stem}-{model_stem}"[: 64 - len(suffix)]
    candidate = f"{base}{suffix}"
    sequence = 2
    while db.scalar(select(CatalogProduct.id).where(CatalogProduct.product_code == candidate)):
        numbered_suffix = f"-{digest}-{sequence}"
        candidate = f"{base[: 64 - len(numbered_suffix)]}{numbered_suffix}"
        sequence += 1
    return candidate
