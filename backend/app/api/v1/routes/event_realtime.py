import asyncio

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import user_has_permission
from app.auth.security import decode_access_token
from app.db.session import SessionLocal
from app.models.event_management import ManagedEvent, ManagedSubEvent
from app.models.identity import User
from app.services.event_access_service import active_event_membership, user_has_sub_event_access
from app.services.event_realtime_service import event_realtime_hub

router = APIRouter(tags=["event realtime"])

REALTIME_ACCESS_RECHECK_SECONDS = 30


def _realtime_access_allowed(
    db: Session,
    email: str,
    sub_event_id: str,
    login_context: str = "standard",
) -> bool:
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if user is None or sub_event is None:
        return False
    event_status = db.scalar(
        select(ManagedEvent.status).where(ManagedEvent.id == sub_event.event_id)
    )
    if event_status in {"completed", "cancelled"}:
        return False
    if (
        login_context == "event"
        and active_event_membership(db, sub_event.event_id, user.id) is None
    ):
        return False
    return user_has_permission(user, "events.manage") or user_has_sub_event_access(
        db, sub_event.event_id, sub_event_id, user.id
    )


@router.websocket("/event-realtime/{sub_event_id}")
async def event_realtime(websocket: WebSocket, sub_event_id: str) -> None:
    protocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
    protocol = next(
        (item.strip() for item in protocols if item.strip().startswith("btsp-token.")), None
    )
    if protocol is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    token = protocol.removeprefix("btsp-token.")
    try:
        token_payload = decode_access_token(token)
        email = token_payload.get("sub")
        login_context = token_payload.get("login_context", "standard")
    except jwt.PyJWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if not isinstance(email, str) or not email:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    with SessionLocal() as db:
        if not _realtime_access_allowed(db, email, sub_event_id, login_context):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    await event_realtime_hub.connect(sub_event_id, websocket, protocol)
    try:
        while True:
            try:
                await asyncio.wait_for(
                    websocket.receive_text(), timeout=REALTIME_ACCESS_RECHECK_SECONDS
                )
            except TimeoutError:
                pass
            try:
                refreshed_payload = decode_access_token(token)
                refreshed_email = refreshed_payload.get("sub")
            except jwt.PyJWTError:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            if (
                refreshed_email != email
                or refreshed_payload.get("login_context", "standard") != login_context
            ):
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            with SessionLocal() as db:
                if not _realtime_access_allowed(db, email, sub_event_id, login_context):
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
    except WebSocketDisconnect:
        pass
    finally:
        event_realtime_hub.disconnect(sub_event_id, websocket)
