from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.catalog import VendorStateExclusion
from app.models.store import Store

US_STATE_CODES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    "DC",
}


class VendorGeographyError(ValueError):
    pass


def get_excluded_states(db: Session, vendor_code: str) -> list[str]:
    return sorted(
        db.scalars(
            select(VendorStateExclusion.state_code).where(
                VendorStateExclusion.vendor_code == vendor_code
            )
        ).all()
    )


def set_excluded_states(db: Session, vendor_code: str, state_codes: list[str]) -> list[str]:
    normalized = {code.strip().upper() for code in state_codes}
    invalid = normalized - US_STATE_CODES
    if invalid:
        raise VendorGeographyError(f"Unknown state codes: {', '.join(sorted(invalid))}")
    db.execute(delete(VendorStateExclusion).where(VendorStateExclusion.vendor_code == vendor_code))
    db.add_all(
        VendorStateExclusion(vendor_code=vendor_code, state_code=code) for code in normalized
    )
    db.commit()
    return sorted(normalized)


def eligible_stores(db: Session, vendor_code: str) -> list[Store]:
    excluded = get_excluded_states(db, vendor_code)
    statement = select(Store).where(Store.is_active.is_(True), Store.is_ordering_enabled.is_(True))
    if excluded:
        statement = statement.where(
            (Store.state_code.is_(None)) | (~Store.state_code.in_(excluded))
        )
    return list(db.scalars(statement.order_by(Store.store_number)).all())


def state_is_excluded(db: Session, vendor_code: str, state_code: str | None) -> bool:
    if not state_code:
        return False
    return (
        db.scalar(
            select(VendorStateExclusion.state_code).where(
                VendorStateExclusion.vendor_code == vendor_code,
                VendorStateExclusion.state_code == state_code.upper(),
            )
        )
        is not None
    )
