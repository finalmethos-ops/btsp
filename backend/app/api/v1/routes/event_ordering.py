from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.event_management import ManagedSubEvent
from app.models.identity import User
from app.schemas.event_ordering import (
    EventEntityOrderWrite,
    EventOrderingAssignmentResponse,
    EventOrderingWorkspaceResponse,
)
from app.services.event_access_service import event_window_open_for_user
from app.services.event_ordering_service import (
    EventOrderingError,
    list_ordering_assignments,
    ordering_workspace,
    submit_entity_order,
)
from app.services.event_realtime_service import event_realtime_hub

router = APIRouter(prefix="/event-ordering", tags=["event entity ordering"])


@router.get("/assignments", response_model=list[EventOrderingAssignmentResponse])
def read_ordering_assignments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EventOrderingAssignmentResponse]:
    return [
        assignment
        for assignment in list_ordering_assignments(db, user)
        if event_window_open_for_user(db, assignment.event_id, user.id)
    ]


def _require_open_event_window(db: Session, sub_event_id: str, user: User) -> None:
    sub_event = db.get(ManagedSubEvent, sub_event_id)
    if sub_event is None:
        return
    if not event_window_open_for_user(db, sub_event.event_id, user.id):
        raise HTTPException(status_code=403, detail="Event access is outside the scheduled window")


@router.get("/{sub_event_id}", response_model=EventOrderingWorkspaceResponse)
def read_ordering_workspace(
    sub_event_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventOrderingWorkspaceResponse:
    _require_open_event_window(db, sub_event_id, user)
    try:
        workspace = ordering_workspace(db, sub_event_id, user)
    except EventOrderingError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if workspace is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    return workspace


@router.put("/{sub_event_id}/order", response_model=EventOrderingWorkspaceResponse)
async def put_entity_order(
    sub_event_id: str,
    payload: EventEntityOrderWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventOrderingWorkspaceResponse:
    _require_open_event_window(db, sub_event_id, user)
    try:
        workspace = submit_entity_order(db, sub_event_id, payload, user)
    except EventOrderingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if workspace is None:
        raise HTTPException(status_code=404, detail="Sub-event not found")
    await event_realtime_hub.publish(sub_event_id, "order.changed")
    return workspace
