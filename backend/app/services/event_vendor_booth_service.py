import re

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalog import CatalogVendor
from app.models.event_management import EventMembership, EventVendorBooth, ManagedEvent
from app.models.identity import User
from app.schemas.event_vendor_booth import EventVendorBoothResponse, EventVendorBoothWrite
from app.services.event_access_service import event_operations_are_locked


class EventVendorBoothError(ValueError):
    pass


def _event_vendor_source(event_id: str) -> str:
    return f"event-only:{event_id}"


def list_available_vendors(db: Session, event_id: str) -> list[CatalogVendor] | None:
    if db.get(ManagedEvent, event_id) is None:
        return None
    return list(
        db.scalars(
            select(CatalogVendor)
            .where(
                or_(
                    CatalogVendor.is_active.is_(True),
                    CatalogVendor.source_file == _event_vendor_source(event_id),
                )
            )
            .order_by(CatalogVendor.name, CatalogVendor.vendor_code)
        ).all()
    )


def create_event_only_vendor(db: Session, event_id: str, name: str) -> CatalogVendor | None:
    event = db.get(ManagedEvent, event_id)
    if event is None:
        return None
    if event_operations_are_locked(db, event_id):
        raise EventVendorBoothError(
            "Event vendor booths are locked because the event is cancelled or settlement is closed"
        )
    base = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")[:36] or "VENDOR"
    prefix = f"EVT-{event.slug.upper()[:16]}-{base}"[:58].rstrip("-")
    code = prefix
    sequence = 2
    while db.scalar(select(CatalogVendor.id).where(CatalogVendor.vendor_code == code)):
        suffix = f"-{sequence}"
        code = f"{prefix[:64 - len(suffix)]}{suffix}"
        sequence += 1
    vendor = CatalogVendor(
        vendor_code=code,
        name=name.strip(),
        is_active=False,
        source_file=_event_vendor_source(event_id),
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def _response(db: Session, booth: EventVendorBooth) -> EventVendorBoothResponse:
    event = db.get(ManagedEvent, booth.event_id)
    vendor = db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == booth.vendor_code))
    return EventVendorBoothResponse(
        id=booth.id,
        event_id=booth.event_id,
        event_name=event.name if event else "Event",
        vendor_code=booth.vendor_code,
        vendor_name=vendor.name if vendor else None,
        booth_name=booth.booth_name,
        booth_number=booth.booth_number,
        location=booth.location,
        description=booth.description,
        contact_name=booth.contact_name,
        contact_email=booth.contact_email,
        website_url=booth.website_url,
        status=booth.status,
        updated_at=booth.updated_at,
    )


def list_event_booths(db: Session, event_id: str) -> list[EventVendorBoothResponse] | None:
    if db.get(ManagedEvent, event_id) is None:
        return None
    booths = db.scalars(
        select(EventVendorBooth)
        .where(EventVendorBooth.event_id == event_id)
        .order_by(EventVendorBooth.booth_name)
    ).all()
    return [_response(db, booth) for booth in booths]


def save_booth(
    db: Session,
    event_id: str,
    payload: EventVendorBoothWrite,
    actor: str,
    booth_id: str | None = None,
) -> EventVendorBoothResponse | None:
    if db.get(ManagedEvent, event_id) is None:
        return None
    if event_operations_are_locked(db, event_id):
        raise EventVendorBoothError(
            "Event vendor booths are locked because the event is cancelled or settlement is closed"
        )
    vendor = db.scalar(
        select(CatalogVendor).where(CatalogVendor.vendor_code == payload.vendor_code)
    )
    if vendor is None or (
        not vendor.is_active and vendor.source_file != _event_vendor_source(event_id)
    ):
        raise EventVendorBoothError("Vendor is not active in the main platform")
    booth = db.get(EventVendorBooth, booth_id) if booth_id else None
    if booth_id and (booth is None or booth.event_id != event_id):
        return None
    if booth is None:
        booth = EventVendorBooth(event_id=event_id)
        db.add(booth)
    for field, value in payload.model_dump().items():
        setattr(booth, field, value)
    booth.updated_by = actor
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise EventVendorBoothError("Vendor already has a booth for this event") from exc
    db.refresh(booth)
    return _response(db, booth)


def my_booths(db: Session, user: User) -> list[EventVendorBoothResponse]:
    memberships = db.scalars(
        select(EventMembership).where(
            EventMembership.user_id == user.id,
            EventMembership.membership_type == "vendor",
            EventMembership.is_active.is_(True),
        )
    ).all()
    if not memberships:
        return []
    clauses = [
        (EventVendorBooth.event_id == membership.event_id)
        & EventVendorBooth.vendor_code.in_(
            list(
                set(membership.vendor_codes or [])
                | ({membership.vendor_code} if membership.vendor_code else set())
            )
        )
        for membership in memberships
    ]
    booths = []
    for clause in clauses:
        booths.extend(db.scalars(select(EventVendorBooth).where(clause)).all())
    return [_response(db, booth) for booth in booths]


def vendor_update_booth(
    db: Session, booth_id: str, payload: EventVendorBoothWrite, user: User
) -> EventVendorBoothResponse | None:
    booth = db.get(EventVendorBooth, booth_id)
    if booth is None:
        return None
    if event_operations_are_locked(db, booth.event_id):
        raise EventVendorBoothError(
            "Event vendor booths are locked because the event is cancelled or settlement is closed"
        )
    membership = db.scalar(
        select(EventMembership).where(
            EventMembership.event_id == booth.event_id,
            EventMembership.user_id == user.id,
            EventMembership.membership_type == "vendor",
            EventMembership.is_active.is_(True),
        )
    )
    allowed_codes = set(membership.vendor_codes or []) if membership else set()
    if membership and membership.vendor_code:
        allowed_codes.add(membership.vendor_code)
    if membership is None or booth.vendor_code not in allowed_codes:
        raise EventVendorBoothError("Vendor booth is not assigned to this user")
    if payload.vendor_code != booth.vendor_code:
        raise EventVendorBoothError("Vendors cannot change booth vendor code")
    for field, value in payload.model_dump().items():
        setattr(booth, field, value)
    booth.updated_by = user.email
    db.commit()
    db.refresh(booth)
    return _response(db, booth)
