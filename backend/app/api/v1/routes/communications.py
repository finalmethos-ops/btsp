from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.communication import (
    InternalMessageCreate,
    InternalMessageResponse,
    MessageRecipient,
)
from app.services.communication_service import (
    CommunicationError,
    list_messages,
    list_recipients,
    mark_message_read,
    send_message,
)

router = APIRouter(prefix="/communications", tags=["communications"])


@router.get("/recipients", response_model=list[MessageRecipient])
def read_recipients(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("communications.read")),
) -> list[MessageRecipient]:
    return [
        MessageRecipient(email=item.email, display_name=item.display_name)
        for item in list_recipients(db, user.email)
    ]


@router.get("/messages", response_model=list[InternalMessageResponse])
def read_messages(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("communications.read")),
) -> list[InternalMessageResponse]:
    return list_messages(db, user.email)


@router.post(
    "/messages",
    response_model=InternalMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_message(
    payload: InternalMessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("communications.send")),
) -> InternalMessageResponse:
    try:
        return send_message(db, user.email, payload)
    except CommunicationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/messages/{message_id}/read", response_model=InternalMessageResponse)
def post_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("communications.read")),
) -> InternalMessageResponse:
    message = mark_message_read(db, message_id, user.email)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return message
