from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.identity import User


class ManagedEvent(Base):
    __tablename__ = "managed_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    slug: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    venue_name: Mapped[str] = mapped_column(String(255))
    address_line1: Mapped[str] = mapped_column(String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(128))
    state_code: Mapped[str] = mapped_column(String(32))
    postal_code: Mapped[str] = mapped_column(String(24))
    country_code: Mapped[str] = mapped_column(String(2), default="US")
    theme_primary_color: Mapped[str] = mapped_column(String(7), default="#07142c")
    theme_accent_color: Mapped[str] = mapped_column(String(7), default="#ffd400")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sub_events: Mapped[list["ManagedSubEvent"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", order_by="ManagedSubEvent.starts_at"
    )
    memberships: Mapped[list["EventMembership"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    branding: Mapped["EventBrandingAsset | None"] = relationship(
        back_populates="event", cascade="all, delete-orphan", uselist=False
    )
    venue_map: Mapped["EventVenueMapAsset | None"] = relationship(
        back_populates="event", cascade="all, delete-orphan", uselist=False
    )


class EventBrandingAsset(Base):
    __tablename__ = "event_branding_assets"

    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), primary_key=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by: Mapped[str] = mapped_column(String(320))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    event: Mapped[ManagedEvent] = relationship(back_populates="branding")


class EventVenueMapAsset(Base):
    __tablename__ = "event_venue_map_assets"

    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), primary_key=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by: Mapped[str] = mapped_column(String(320))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    event: Mapped[ManagedEvent] = relationship(back_populates="venue_map")


class ManagedSubEvent(Base):
    __tablename__ = "managed_sub_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    location: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), default="draft")
    module_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    capacity: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    event: Mapped[ManagedEvent] = relationship(back_populates="sub_events")
    product_slides: Mapped[list["EventProductSlide"]] = relationship(
        back_populates="sub_event",
        cascade="all, delete-orphan",
        order_by="EventProductSlide.position",
    )


class EventProductSlide(Base):
    __tablename__ = "event_product_slides"
    __table_args__ = (UniqueConstraint("sub_event_id", "position", name="uq_event_slide_position"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    sub_event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_sub_events.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(index=True)
    slide_type: Mapped[str] = mapped_column(String(24), default="product", index=True)
    filler_category: Mapped[str | None] = mapped_column(String(24), nullable=True)
    catalog_product_code: Mapped[str | None] = mapped_column(
        ForeignKey("catalog_products.product_code", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    model_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    vendor_code: Mapped[str | None] = mapped_column(
        ForeignKey("catalog_vendors.vendor_code", ondelete="RESTRICT"), nullable=True, index=True
    )
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    specifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    standard_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    minimum_order_quantity: Mapped[int] = mapped_column(default=1)
    available_inventory: Mapped[int | None] = mapped_column(nullable=True)
    max_event_units: Mapped[int | None] = mapped_column(nullable=True)
    allow_waitlist: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_window_start: Mapped[date | None] = mapped_column(nullable=True)
    delivery_window_end: Mapped[date | None] = mapped_column(nullable=True)
    vendor_delivery_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    presenter_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_variants: Mapped[list[dict]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sub_event: Mapped[ManagedSubEvent] = relationship(back_populates="product_slides")
    image: Mapped["EventProductSlideImage | None"] = relationship(
        back_populates="slide", cascade="all, delete-orphan", uselist=False
    )
    vendor_logo: Mapped["EventProductSlideVendorLogo | None"] = relationship(
        back_populates="slide", cascade="all, delete-orphan", uselist=False
    )


class EventProductSlideImage(Base):
    __tablename__ = "event_product_slide_images"

    slide_id: Mapped[str] = mapped_column(
        ForeignKey("event_product_slides.id", ondelete="CASCADE"), primary_key=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by: Mapped[str] = mapped_column(String(320))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    slide: Mapped[EventProductSlide] = relationship(back_populates="image")


class EventProductSlideVendorLogo(Base):
    __tablename__ = "event_product_slide_vendor_logos"

    slide_id: Mapped[str] = mapped_column(
        ForeignKey("event_product_slides.id", ondelete="CASCADE"), primary_key=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by: Mapped[str] = mapped_column(String(320))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    slide: Mapped[EventProductSlide] = relationship(back_populates="vendor_logo")


class EventPresentationState(Base):
    __tablename__ = "event_presentation_states"

    sub_event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_sub_events.id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    current_slide_id: Mapped[str | None] = mapped_column(
        ForeignKey("event_product_slides.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(24), default="idle", index=True)
    ordering_status: Mapped[str] = mapped_column(String(24), default="closed")
    ordering_opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_by: Mapped[str] = mapped_column(String(320))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    current_slide: Mapped[EventProductSlide | None] = relationship()


class EventMembership(Base):
    __tablename__ = "event_memberships"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_membership_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    membership_type: Mapped[str] = mapped_column(String(24), index=True)
    loadout_role: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    vendor_code: Mapped[str | None] = mapped_column(
        ForeignKey("catalog_vendors.vendor_code", ondelete="RESTRICT"), nullable=True, index=True
    )
    vendor_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    entity_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    module_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    task_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sub_event_scope_configured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    event: Mapped[ManagedEvent] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship()
    sub_event_registrations: Mapped[list["EventSubEventRegistration"]] = relationship(
        back_populates="membership", cascade="all, delete-orphan"
    )


class EventEntityOrder(Base):
    __tablename__ = "event_entity_orders"
    __table_args__ = (
        UniqueConstraint("sub_event_id", "slide_id", "entity_code", name="uq_event_entity_order"),
        Index("ix_event_entity_orders_slide_status", "slide_id", "status"),
        Index(
            "ix_event_entity_orders_sub_event_entity_status",
            "sub_event_id",
            "entity_code",
            "status",
        ),
        Index(
            "ix_event_entity_orders_event_entity_status",
            "event_id",
            "entity_code",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    sub_event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_sub_events.id", ondelete="CASCADE"), index=True
    )
    slide_id: Mapped[str] = mapped_column(
        ForeignKey("event_product_slides.id", ondelete="RESTRICT"), index=True
    )
    membership_id: Mapped[str] = mapped_column(
        ForeignKey("event_memberships.id", ondelete="RESTRICT")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    entity_code: Mapped[str] = mapped_column(String(64), index=True)
    quantity: Mapped[int]
    requested_delivery_start: Mapped[date]
    requested_delivery_end: Mapped[date]
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    status: Mapped[str] = mapped_column(String(24), index=True)
    variant_quantities: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    review_status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventEntityOrderRevision(Base):
    __tablename__ = "event_entity_order_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("event_entity_orders.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[int]
    quantity: Mapped[int]
    requested_delivery_start: Mapped[date]
    requested_delivery_end: Mapped[date]
    status: Mapped[str] = mapped_column(String(24))
    changed_by: Mapped[str] = mapped_column(String(320))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventOrderReviewEvent(Base):
    __tablename__ = "event_order_review_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("event_entity_orders.id", ondelete="CASCADE"), index=True
    )
    decision: Mapped[str] = mapped_column(String(24), index=True)
    previous_quantity: Mapped[int]
    resulting_quantity: Mapped[int]
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventOrderReleaseBatch(Base):
    __tablename__ = "event_order_release_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="staged", index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventOrderReleaseLine(Base):
    __tablename__ = "event_order_release_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(
        ForeignKey("event_order_release_batches.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[str] = mapped_column(
        ForeignKey("event_entity_orders.id", ondelete="RESTRICT"), index=True
    )
    purchase_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("purchase_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vendor_code: Mapped[str] = mapped_column(String(64), index=True)
    entity_code: Mapped[str] = mapped_column(String(64), index=True)
    model_number: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[int]
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    requested_delivery_start: Mapped[date]
    requested_delivery_end: Mapped[date]


class EventOrderBackupArtifact(Base):
    __tablename__ = "event_order_backup_artifacts"
    __table_args__ = (UniqueConstraint("event_id", name="uq_event_order_backup_artifact_event"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="RESTRICT"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(160))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventPoll(Base):
    __tablename__ = "event_polls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    sub_event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_sub_events.id", ondelete="CASCADE"), index=True
    )
    slide_id: Mapped[str | None] = mapped_column(
        ForeignKey("event_product_slides.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    show_results: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    options: Mapped[list["EventPollOption"]] = relationship(
        back_populates="poll", cascade="all, delete-orphan", order_by="EventPollOption.position"
    )


class EventPollOption(Base):
    __tablename__ = "event_poll_options"
    __table_args__ = (
        UniqueConstraint("poll_id", "position", name="uq_event_poll_option_position"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    poll_id: Mapped[str] = mapped_column(
        ForeignKey("event_polls.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    label: Mapped[str] = mapped_column(String(500))

    poll: Mapped[EventPoll] = relationship(back_populates="options")


class EventPollVote(Base):
    __tablename__ = "event_poll_votes"
    __table_args__ = (UniqueConstraint("poll_id", "user_id", name="uq_event_poll_user_vote"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    poll_id: Mapped[str] = mapped_column(
        ForeignKey("event_polls.id", ondelete="CASCADE"), index=True
    )
    option_id: Mapped[str] = mapped_column(
        ForeignKey("event_poll_options.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventAttendance(Base):
    __tablename__ = "event_attendance"
    __table_args__ = (
        UniqueConstraint("sub_event_id", "membership_id", name="uq_event_attendance_member"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    sub_event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_sub_events.id", ondelete="CASCADE"), index=True
    )
    membership_id: Mapped[str] = mapped_column(
        ForeignKey("event_memberships.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="registered", index=True)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[str] = mapped_column(String(320))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventSubEventRegistration(Base):
    __tablename__ = "event_sub_event_registrations"
    __table_args__ = (
        UniqueConstraint("sub_event_id", "membership_id", name="uq_event_sub_event_registration"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    sub_event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_sub_events.id", ondelete="CASCADE"), index=True
    )
    membership_id: Mapped[str] = mapped_column(
        ForeignKey("event_memberships.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    assigned_by: Mapped[str] = mapped_column(String(320))
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    membership: Mapped[EventMembership] = relationship(back_populates="sub_event_registrations")


class EventCalendarEntry(Base):
    __tablename__ = "event_calendar_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    sub_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("managed_sub_events.id", ondelete="CASCADE"), nullable=True, index=True
    )
    entry_type: Mapped[str] = mapped_column(String(24), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visibility_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sub_event: Mapped[ManagedSubEvent | None] = relationship()


class EventAnnouncement(Base):
    __tablename__ = "event_announcements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    sub_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("managed_sub_events.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(24), index=True)
    visibility_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    publishes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventStaffTask(Base):
    __tablename__ = "event_staff_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    sub_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("managed_sub_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    vendor_hall_booth_id: Mapped[str | None] = mapped_column(
        ForeignKey("vendor_hall_booths.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_membership_id: Mapped[str] = mapped_column(
        ForeignKey("event_memberships.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(24), default="normal", index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    status_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_phase: Mapped[str] = mapped_column(String(24), default="live_event", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sub_event: Mapped[ManagedSubEvent | None] = relationship()
    assigned_membership: Mapped[EventMembership] = relationship()


class EventStaffTaskAttachment(Base):
    __tablename__ = "event_staff_task_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(
        ForeignKey("event_staff_tasks.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventVendorBooth(Base):
    __tablename__ = "event_vendor_booths"
    __table_args__ = (UniqueConstraint("event_id", "vendor_code", name="uq_event_vendor_booth"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    vendor_code: Mapped[str] = mapped_column(
        ForeignKey("catalog_vendors.vendor_code", ondelete="RESTRICT"), index=True
    )
    booth_name: Mapped[str] = mapped_column(String(255))
    booth_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    updated_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VendorHallEvent(Base):
    __tablename__ = "vendor_hall_events"
    __table_args__ = (UniqueConstraint("event_id", "sub_event_id", name="uq_vendor_hall_event"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    sub_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("managed_sub_events.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    vendor_submission_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    staff_checkin_opens_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    staff_checkin_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    allow_vendor_edits_after_submission: Mapped[bool] = mapped_column(Boolean, default=False)
    require_staff_checkin: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    event: Mapped[ManagedEvent] = relationship()
    sub_event: Mapped[ManagedSubEvent | None] = relationship()
    booths: Mapped[list["VendorHallBooth"]] = relationship(
        back_populates="vendor_hall_event", cascade="all, delete-orphan"
    )


class VendorHallBooth(Base):
    __tablename__ = "vendor_hall_booths"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "vendor_code",
            "booth_number",
            name="uq_vendor_hall_booth_identity",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vendor_hall_event_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_events.id", ondelete="CASCADE"), index=True
    )
    event_vendor_booth_id: Mapped[str | None] = mapped_column(
        ForeignKey("event_vendor_booths.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_staff_membership_id: Mapped[str | None] = mapped_column(
        ForeignKey("event_memberships.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    vendor_code: Mapped[str] = mapped_column(
        ForeignKey("catalog_vendors.vendor_code", ondelete="RESTRICT"), index=True
    )
    booth_number: Mapped[str] = mapped_column(String(64), default="", index=True)
    booth_name: Mapped[str] = mapped_column(String(255))
    floor_map_zone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    map_x: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    map_y: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    map_width: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    map_height: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    map_manually_adjusted: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    checkin_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checkin_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checked_in_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    admin_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    admin_reviewed_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vendor_hall_event: Mapped[VendorHallEvent] = relationship(back_populates="booths")
    inventory_items: Mapped[list["VendorHallInventoryItem"]] = relationship(
        back_populates="booth", cascade="all, delete-orphan"
    )


class VendorHallSavedBooth(Base):
    __tablename__ = "vendor_hall_saved_booths"
    __table_args__ = (
        UniqueConstraint(
            "membership_id",
            "vendor_hall_booth_id",
            name="uq_vendor_hall_saved_booth_membership",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    membership_id: Mapped[str] = mapped_column(
        ForeignKey("event_memberships.id", ondelete="CASCADE"), index=True
    )
    vendor_hall_booth_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    visited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VendorHallInventoryImport(Base):
    __tablename__ = "vendor_hall_inventory_imports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vendor_hall_booth_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    row_count: Mapped[int] = mapped_column(default=0)
    accepted_count: Mapped[int] = mapped_column(default=0)
    rejected_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(320))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VendorHallInventoryItem(Base):
    __tablename__ = "vendor_hall_inventory_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vendor_hall_booth_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    vendor_code: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual", index=True)
    source_import_id: Mapped[str | None] = mapped_column(
        ForeignKey("vendor_hall_inventory_imports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    model_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    item_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity_expected: Mapped[int] = mapped_column(default=1)
    quantity_checked_in: Mapped[int] = mapped_column(default=0)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    condition: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    status: Mapped[str] = mapped_column(String(32), default="expected", index=True)
    available_for_sale: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sell_to_buddys_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    vendor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    staff_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    booth: Mapped[VendorHallBooth] = relationship(back_populates="inventory_items")


class VendorHallItemAttachment(Base):
    __tablename__ = "vendor_hall_item_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inventory_item_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_inventory_items.id", ondelete="CASCADE"), index=True
    )
    attachment_type: Mapped[str] = mapped_column(String(32), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by: Mapped[str] = mapped_column(String(320))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class VendorHallItemCheckin(Base):
    __tablename__ = "vendor_hall_item_checkins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    inventory_item_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_inventory_items.id", ondelete="CASCADE"), index=True
    )
    vendor_hall_booth_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    quantity_checked: Mapped[int] = mapped_column(default=0)
    condition: Mapped[str | None] = mapped_column(String(32), nullable=True)
    damage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    exception_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_by: Mapped[str] = mapped_column(String(320))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VendorHallBoothCheckin(Base):
    __tablename__ = "vendor_hall_booth_checkins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vendor_hall_booth_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    started_by: Mapped[str] = mapped_column(String(320))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    items_expected: Mapped[int] = mapped_column(default=0)
    items_checked: Mapped[int] = mapped_column(default=0)
    exceptions_count: Mapped[int] = mapped_column(default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class VendorHallException(Base):
    __tablename__ = "vendor_hall_exceptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vendor_hall_booth_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_booths.id", ondelete="CASCADE"), index=True
    )
    inventory_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("vendor_hall_inventory_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    exception_type: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(24), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    description: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class VendorHallFloorMap(Base):
    __tablename__ = "vendor_hall_floor_maps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    vendor_hall_event_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_events.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    image_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    image_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    layout_json: Mapped[dict] = mapped_column(JSON, default=dict)
    uploaded_by: Mapped[str] = mapped_column(String(320))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class VendorHallAuditLog(Base):
    __tablename__ = "vendor_hall_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    vendor_hall_event_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_events.id", ondelete="CASCADE"), index=True
    )
    vendor_hall_booth_id: Mapped[str | None] = mapped_column(
        ForeignKey("vendor_hall_booths.id", ondelete="SET NULL"), nullable=True, index=True
    )
    inventory_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("vendor_hall_inventory_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(320))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StoreLoadoutEvent(Base):
    __tablename__ = "store_loadout_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_store_loadout_event"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    loadout_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    default_loadout_zone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    venue_departure_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    dock_master_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    event: Mapped[ManagedEvent] = relationship()
    assignments: Mapped[list["StoreLoadoutAssignment"]] = relationship(
        back_populates="loadout_event", cascade="all, delete-orphan"
    )


class StoreLoadoutAssignment(Base):
    __tablename__ = "store_loadout_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    store_loadout_event_id: Mapped[str] = mapped_column(
        ForeignKey("store_loadout_events.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    store_number: Mapped[str] = mapped_column(String(32), index=True)
    entity_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="not_started", index=True)
    pickup_priority: Mapped[int] = mapped_column(default=100, index=True)
    loadout_zone: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    distance_miles: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    estimated_drive_minutes: Mapped[int | None] = mapped_column(nullable=True)
    recommended_departure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    team_member_emails: Mapped[list] = mapped_column(JSON, default=list)
    team_lead_emails: Mapped[list] = mapped_column(JSON, default=list)
    vehicle_labels: Mapped[list] = mapped_column(JSON, default=list)
    vehicle_statuses: Mapped[dict] = mapped_column(JSON, default=dict)
    final_review_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    final_review_requested_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    final_review_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    final_review_completed_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    final_review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_by: Mapped[str] = mapped_column(String(320))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    loadout_event: Mapped[StoreLoadoutEvent] = relationship(back_populates="assignments")
    items: Mapped[list["StoreLoadoutItem"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class StoreLoadoutItem(Base):
    __tablename__ = "store_loadout_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("store_loadout_assignments.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    vendor_hall_booth_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_booths.id", ondelete="RESTRICT"), index=True
    )
    vendor_hall_inventory_item_id: Mapped[str] = mapped_column(
        ForeignKey("vendor_hall_inventory_items.id", ondelete="RESTRICT"), index=True
    )
    vendor_code: Mapped[str] = mapped_column(String(64), index=True)
    booth_number: Mapped[str] = mapped_column(String(64), default="", index=True)
    item_name: Mapped[str] = mapped_column(String(255))
    model_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    quantity_assigned: Mapped[int] = mapped_column(default=1)
    quantity_found: Mapped[int] = mapped_column(default=0)
    condition: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    status: Mapped[str] = mapped_column(String(32), default="assigned", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    damage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assignment: Mapped[StoreLoadoutAssignment] = relationship(back_populates="items")


class StoreLoadoutItemAttachment(Base):
    __tablename__ = "store_loadout_item_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("store_loadout_assignments.id", ondelete="CASCADE"), index=True
    )
    loadout_item_id: Mapped[str] = mapped_column(
        ForeignKey("store_loadout_items.id", ondelete="CASCADE"), index=True
    )
    attachment_type: Mapped[str] = mapped_column(String(32), default="photo", index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StoreLoadoutItemCheckin(Base):
    __tablename__ = "store_loadout_item_checkins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    loadout_item_id: Mapped[str] = mapped_column(
        ForeignKey("store_loadout_items.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("store_loadout_assignments.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    quantity_found: Mapped[int] = mapped_column(default=0)
    damage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_by: Mapped[str] = mapped_column(String(320))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StoreLoadoutSignoff(Base):
    __tablename__ = "store_loadout_signoffs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("store_loadout_assignments.id", ondelete="CASCADE"), index=True
    )
    signer_name: Mapped[str] = mapped_column(String(255))
    signer_email: Mapped[str] = mapped_column(String(320))
    signature_text: Mapped[str] = mapped_column(String(255))
    exception_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StoreLoadoutAuditLog(Base):
    __tablename__ = "store_loadout_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    store_loadout_event_id: Mapped[str] = mapped_column(
        ForeignKey("store_loadout_events.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("store_loadout_assignments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    loadout_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("store_loadout_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(320))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventSettlementEvent(Base):
    __tablename__ = "event_settlement_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_event_settlement_event"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    event: Mapped[ManagedEvent] = relationship()
    exceptions: Mapped[list["EventSettlementException"]] = relationship(
        back_populates="settlement_event", cascade="all, delete-orphan"
    )


class EventSettlementException(Base):
    __tablename__ = "event_settlement_exceptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    settlement_event_id: Mapped[str] = mapped_column(
        ForeignKey("event_settlement_events.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    exception_type: Mapped[str] = mapped_column(String(48), index=True)
    severity: Mapped[str] = mapped_column(String(24), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    reference_type: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    settlement_event: Mapped[EventSettlementEvent] = relationship(back_populates="exceptions")


class EventSettlementAuditLog(Base):
    __tablename__ = "event_settlement_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    settlement_event_id: Mapped[str] = mapped_column(
        ForeignKey("event_settlement_events.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(320))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventFeedbackResponse(Base):
    __tablename__ = "event_feedback_responses"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_feedback_response_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_id: Mapped[str] = mapped_column(
        ForeignKey("managed_events.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column()
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
