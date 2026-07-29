from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.communication import InternalMessage
from app.models.event_snapshot import EventSnapshot
from app.models.identity import User
from app.schemas.communication import InternalMessageCreate


class CommunicationError(ValueError):
    pass


def list_recipients(db: Session, sender_email: str) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.is_active.is_(True), User.email != sender_email)
            .order_by(User.display_name, User.email)
        ).all()
    )


def list_messages(db: Session, email: str) -> list[InternalMessage]:
    return list(
        db.scalars(
            select(InternalMessage)
            .where(
                or_(
                    InternalMessage.sender_email == email,
                    InternalMessage.recipient_email == email,
                )
            )
            .order_by(InternalMessage.created_at.desc(), InternalMessage.id.desc())
            .limit(500)
        ).all()
    )


def send_message(
    db: Session,
    sender_email: str,
    payload: InternalMessageCreate,
) -> InternalMessage:
    conversation_id = str(uuid4())
    if payload.reply_to_message_id is not None:
        original = db.scalar(
            select(InternalMessage).where(
                InternalMessage.id == payload.reply_to_message_id,
                or_(
                    InternalMessage.sender_email == sender_email,
                    InternalMessage.recipient_email == sender_email,
                ),
            )
        )
        if original is None:
            raise CommunicationError("Reply target was not found in your messages")
        other_participant = (
            original.recipient_email
            if original.sender_email == sender_email
            else original.sender_email
        )
        if payload.recipient_email != other_participant:
            raise CommunicationError("Replies must remain within the original conversation")
        conversation_id = original.conversation_id
    recipient = db.scalar(
        select(User).where(
            User.email == payload.recipient_email,
            User.is_active.is_(True),
        )
    )
    if recipient is None:
        raise CommunicationError("Recipient is not an active BTSP user")
    message = InternalMessage(
        conversation_id=conversation_id,
        sender_email=sender_email,
        recipient_email=recipient.email,
        subject=payload.subject.strip(),
        body=payload.body.strip(),
    )
    db.add(message)
    db.flush()
    db.add(
        EventSnapshot(
            event_type="communication.message.sent",
            entity_type="internal_message",
            entity_id=str(message.id),
            actor=sender_email,
            payload={"recipient_email": recipient.email, "subject": message.subject},
        )
    )
    db.commit()
    db.refresh(message)
    return message


def mark_message_read(db: Session, message_id: int, recipient_email: str) -> InternalMessage | None:
    message = db.scalar(
        select(InternalMessage).where(
            InternalMessage.id == message_id,
            InternalMessage.recipient_email == recipient_email,
        )
    )
    if message is None:
        return None
    if message.read_at is None:
        message.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(message)
    return message
