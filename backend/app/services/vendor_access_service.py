from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import CatalogVendor
from app.models.identity import User, user_vendor_access


def vendor_codes_for_user(db: Session, user: User) -> list[str]:
    codes = set(
        db.scalars(
            select(user_vendor_access.c.vendor_code).where(user_vendor_access.c.user_id == user.id)
        ).all()
    )
    if user.vendor_code:
        codes.add(user.vendor_code)
    return sorted(codes)


def vendor_accounts_for_user(db: Session, user: User) -> list[CatalogVendor]:
    codes = vendor_codes_for_user(db, user)
    if not codes:
        return []
    return list(
        db.scalars(
            select(CatalogVendor)
            .where(CatalogVendor.vendor_code.in_(codes), CatalogVendor.is_active.is_(True))
            .order_by(CatalogVendor.name)
        ).all()
    )


def user_has_vendor_access(db: Session, user: User, vendor_code: str) -> bool:
    return vendor_code in vendor_codes_for_user(db, user)
