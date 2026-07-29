from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.communication import InternalMessage
from app.models.identity import User
from app.schemas.communication import InternalMessageCreate
from app.services.communication_service import (
    list_messages,
    mark_message_read,
    send_message,
)


def test_internal_message_is_private_and_can_be_marked_read() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                User(
                    email="sender@example.com",
                    display_name="Sender",
                    password_hash="unused",
                    is_active=True,
                ),
                User(
                    email="recipient@example.com",
                    display_name="Recipient",
                    password_hash="unused",
                    is_active=True,
                ),
                User(
                    email="other@example.com",
                    display_name="Other",
                    password_hash="unused",
                    is_active=True,
                ),
            ]
        )
        db.commit()

        message = send_message(
            db,
            "sender@example.com",
            InternalMessageCreate(
                recipient_email="recipient@example.com",
                subject="Invoice question",
                body="Please review the quantity mismatch.",
            ),
        )

        assert [item.id for item in list_messages(db, "sender@example.com")] == [message.id]
        assert [item.id for item in list_messages(db, "recipient@example.com")] == [message.id]
        assert list_messages(db, "other@example.com") == []
        assert mark_message_read(db, message.id, "other@example.com") is None
        read = mark_message_read(db, message.id, "recipient@example.com")
        assert isinstance(read, InternalMessage)
        assert read.read_at is not None

        reply = send_message(
            db,
            "recipient@example.com",
            InternalMessageCreate(
                recipient_email="sender@example.com",
                subject="Re: Invoice question",
                body="The corrected invoice is attached.",
                reply_to_message_id=message.id,
            ),
        )
        assert reply.conversation_id == message.conversation_id
        assert [item.id for item in list_messages(db, "sender@example.com")] == [
            reply.id,
            message.id,
        ]
