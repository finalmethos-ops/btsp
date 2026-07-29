from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.responses import content_disposition
from app.auth.dependencies import get_current_user
from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.event_staff_task import (
    EventStaffTaskAttachmentResponse,
    EventStaffTaskResponse,
    EventStaffTaskStatusWrite,
    EventStaffTaskWrite,
)
from app.services.event_staff_task_report_service import (
    EXCEL_CONTENT_TYPE,
    export_event_staff_tasks,
)
from app.services.event_staff_task_service import (
    MAX_TASK_EVIDENCE_BYTES,
    EventStaffTaskAccessError,
    EventStaffTaskError,
    attach_task_evidence,
    list_event_tasks,
    my_tasks,
    save_event_task,
    task_evidence_content,
    update_task_status,
)

router = APIRouter(prefix="/event-staff-tasks", tags=["event staff tasks"])


@router.get("/events/{event_id}/export.xlsx")
def get_event_task_export(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> StreamingResponse:
    report = export_event_staff_tasks(db, event_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Event not found")
    filename, content = report
    return StreamingResponse(
        BytesIO(content),
        media_type=EXCEL_CONTENT_TYPE,
        headers={"Content-Disposition": content_disposition(filename)},
    )


@router.post(
    "/{task_id}/attachments",
    response_model=EventStaffTaskAttachmentResponse,
)
async def post_task_attachment(
    task_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventStaffTaskAttachmentResponse:
    content = await file.read(MAX_TASK_EVIDENCE_BYTES + 1)
    try:
        attachment = attach_task_evidence(
            db,
            task_id,
            file.filename or "evidence",
            file.content_type or "application/octet-stream",
            content,
            user,
        )
    except EventStaffTaskAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except EventStaffTaskError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if attachment is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return attachment


@router.get("/{task_id}/attachments/{attachment_id}/content")
def get_task_attachment(
    task_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    source = task_evidence_content(db, task_id, attachment_id, user)
    if source is None:
        raise HTTPException(status_code=404, detail="Task evidence not found")
    filename, content_type, content = source
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": content_disposition(filename),
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/mine", response_model=list[EventStaffTaskResponse])
def read_my_tasks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EventStaffTaskResponse]:
    return my_tasks(db, user)


@router.get("/{event_id}", response_model=list[EventStaffTaskResponse])
def read_event_tasks(
    event_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("events.manage")),
) -> list[EventStaffTaskResponse]:
    tasks = list_event_tasks(db, event_id)
    if tasks is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return tasks


@router.post("/{event_id}", response_model=EventStaffTaskResponse)
def post_event_task(
    event_id: str,
    payload: EventStaffTaskWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventStaffTaskResponse:
    try:
        task = save_event_task(db, event_id, payload, user.email)
    except EventStaffTaskError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if task is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return task


@router.put("/{event_id}/{task_id}", response_model=EventStaffTaskResponse)
def put_event_task(
    event_id: str,
    task_id: str,
    payload: EventStaffTaskWrite,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("events.manage")),
) -> EventStaffTaskResponse:
    try:
        task = save_event_task(db, event_id, payload, user.email, task_id)
    except EventStaffTaskError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}/status", response_model=EventStaffTaskResponse)
def patch_task_status(
    task_id: str,
    payload: EventStaffTaskStatusWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventStaffTaskResponse:
    try:
        task = update_task_status(db, task_id, payload, user)
    except EventStaffTaskError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
