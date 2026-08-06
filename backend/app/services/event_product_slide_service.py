from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import CatalogProduct, CatalogVendor
from app.models.event_management import (
    EventPresentationState,
    EventProductSlide,
    EventProductSlideImage,
    ManagedSubEvent,
)
from app.schemas.event_product_slide import (
    EventProductSlideResponse,
    EventProductSlideWrite,
)
from app.services.event_access_service import event_operations_are_locked
from app.services.upload_validation import content_matches_declared_type


class EventProductSlideError(ValueError):
    pass


def purge_event_slide_images(db: Session, event_id: str) -> int:
    """Remove stored presentation image bytes after an event is concluded."""
    slide_ids = select(EventProductSlide.id).where(EventProductSlide.event_id == event_id)
    result = db.execute(
        delete(EventProductSlideImage).where(EventProductSlideImage.slide_id.in_(slide_ids))
    )
    return result.rowcount or 0


def _slides_enabled(sub_event: ManagedSubEvent) -> None:
    if "product-slides" not in sub_event.module_codes:
        raise EventProductSlideError("Product slides are not enabled for this sub-event")


def _response(slide: EventProductSlide) -> EventProductSlideResponse:
    return EventProductSlideResponse.model_validate(slide, from_attributes=True).model_copy(
        update={"has_image": slide.image is not None}
    )


def _slide_query():
    return select(EventProductSlide).options(selectinload(EventProductSlide.image))


def list_slides(db: Session, sub_event_id: str) -> list[EventProductSlideResponse] | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _slides_enabled(sub_event)
    slides = db.scalars(
        _slide_query()
        .where(EventProductSlide.sub_event_id == sub_event_id)
        .order_by(EventProductSlide.position)
    ).all()
    return [_response(slide) for slide in slides]


def _validate_product(db: Session, payload: EventProductSlideWrite) -> None:
    if payload.slide_type == "filler":
        return
    vendor = db.scalar(
        select(CatalogVendor).where(
            CatalogVendor.vendor_code == payload.vendor_code,
            CatalogVendor.is_active.is_(True),
        )
    )
    if vendor is None:
        raise EventProductSlideError("Vendor is not active in the main platform")
    if payload.catalog_product_code:
        product = db.scalar(
            select(CatalogProduct).where(
                CatalogProduct.product_code == payload.catalog_product_code
            )
        )
        if product is None:
            raise EventProductSlideError("Catalog model was not found")
        if product.vendor_code != payload.vendor_code:
            raise EventProductSlideError("Catalog model belongs to a different vendor")


def _slide_values(payload: EventProductSlideWrite) -> dict:
    values = payload.model_dump(exclude={"product_variants"})
    values["product_variants"] = [
        variant.model_dump(mode="json") for variant in payload.product_variants
    ]
    if payload.slide_type == "filler":
        values.update(
            catalog_product_code=None,
            model_number=None,
            vendor_code=None,
            category=None,
            event_unit_cost=None,
            standard_cost=None,
            minimum_order_quantity=1,
            available_inventory=None,
            max_event_units=None,
            allow_waitlist=False,
            delivery_window_start=None,
            delivery_window_end=None,
            vendor_delivery_notes=None,
            product_variants=[],
        )
    else:
        values["filler_category"] = None
    return values


def create_slide(
    db: Session,
    sub_event_id: str,
    payload: EventProductSlideWrite,
    actor: str,
) -> EventProductSlideResponse | None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return None
    _slides_enabled(sub_event)
    if event_operations_are_locked(db, sub_event.event_id):
        raise EventProductSlideError(
            "Product slides are locked because the event is cancelled or settlement is closed"
        )
    _validate_product(db, payload)
    last_position = db.scalar(
        select(func.max(EventProductSlide.position)).where(
            EventProductSlide.sub_event_id == sub_event_id
        )
    )
    values = _slide_values(payload)
    slide = EventProductSlide(
        event_id=sub_event.event_id,
        sub_event_id=sub_event_id,
        position=(last_position or 0) + 1,
        created_by=actor,
        **values,
    )
    db.add(slide)
    db.commit()
    db.refresh(slide)
    return _response(db.scalar(_slide_query().where(EventProductSlide.id == slide.id)))


def update_slide(
    db: Session, slide_id: str, payload: EventProductSlideWrite
) -> EventProductSlideResponse | None:
    slide = db.scalar(_slide_query().where(EventProductSlide.id == slide_id))
    if slide is None:
        return None
    if event_operations_are_locked(db, slide.event_id):
        raise EventProductSlideError(
            "Product slides are locked because the event is cancelled or settlement is closed"
        )
    _slides_enabled(db.get(ManagedSubEvent, slide.sub_event_id))
    _validate_product(db, payload)
    values = _slide_values(payload)
    for field, value in values.items():
        setattr(slide, field, value)
    db.commit()
    return _response(db.scalar(_slide_query().where(EventProductSlide.id == slide_id)))


def delete_slide(db: Session, slide_id: str) -> bool | None:
    slide = db.scalar(_slide_query().where(EventProductSlide.id == slide_id))
    if slide is None:
        return None
    if event_operations_are_locked(db, slide.event_id):
        raise EventProductSlideError(
            "Product slides are locked because the event is cancelled or settlement is closed"
        )
    remaining = db.scalars(
        _slide_query()
        .where(EventProductSlide.sub_event_id == slide.sub_event_id)
        .where(EventProductSlide.id != slide_id)
        .order_by(EventProductSlide.position, EventProductSlide.created_at)
    ).all()
    state = db.get(EventPresentationState, slide.sub_event_id)
    if state is not None and state.current_slide_id == slide_id:
        # Clear the FK before deleting the referenced row. Otherwise databases
        # enforcing referential integrity can reject an otherwise valid delete.
        state.current_slide_id = remaining[0].id if remaining else None
    db.delete(slide)
    db.flush()
    for position, item in enumerate(remaining, start=1):
        item.position = position
    db.commit()
    return True


def reorder_slides(
    db: Session, sub_event_id: str, slide_ids: list[str]
) -> list[EventProductSlideResponse] | None:
    slides = list(
        db.scalars(_slide_query().where(EventProductSlide.sub_event_id == sub_event_id)).all()
    )
    if not slides and db.get(ManagedSubEvent, sub_event_id) is None:
        return None
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is not None:
        _slides_enabled(sub_event)
        if event_operations_are_locked(db, sub_event.event_id):
            raise EventProductSlideError(
                "Product slides are locked because the event is cancelled or settlement is closed"
            )
    if set(slide_ids) != {slide.id for slide in slides} or len(slide_ids) != len(slides):
        raise EventProductSlideError("Slide order must include every slide exactly once")
    by_id = {slide.id: slide for slide in slides}
    for offset, slide in enumerate(slides, start=1):
        slide.position = -offset
    db.flush()
    for position, slide_id in enumerate(slide_ids, start=1):
        by_id[slide_id].position = position
    db.commit()
    return list_slides(db, sub_event_id)


def save_slide_image(
    db: Session,
    slide_id: str,
    filename: str,
    content_type: str,
    content: bytes,
    actor: str,
) -> EventProductSlideResponse | None:
    slide = db.get(EventProductSlide, slide_id)
    if slide is None:
        return None
    if event_operations_are_locked(db, slide.event_id):
        raise EventProductSlideError(
            "Product slides are locked because the event is cancelled or settlement is closed"
        )
    _slides_enabled(db.get(ManagedSubEvent, slide.sub_event_id))
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise EventProductSlideError("Product image must be PNG, JPEG, or WebP")
    if not content or len(content) > 8 * 1024 * 1024:
        raise EventProductSlideError("Product image must be between 1 byte and 8 MB")
    if not content_matches_declared_type(content, content_type):
        raise EventProductSlideError("Product image content does not match its declared type")
    image = db.get(EventProductSlideImage, slide_id)
    if image is None:
        image = EventProductSlideImage(slide_id=slide_id)
        db.add(image)
    image.filename = filename[:255]
    image.content_type = content_type
    image.content = content
    image.uploaded_by = actor
    db.commit()
    return _response(db.scalar(_slide_query().where(EventProductSlide.id == slide_id)))
