from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class InternalMessage(Base):
    __tablename__ = "internal_messages"
    __table_args__ = (
        Index("ix_internal_messages_recipient_created", "recipient_email", "created_at"),
        Index("ix_internal_messages_sender_created", "sender_email", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    sender_email: Mapped[str] = mapped_column(String(320), ForeignKey("users.email"))
    recipient_email: Mapped[str] = mapped_column(String(320), ForeignKey("users.email"))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
