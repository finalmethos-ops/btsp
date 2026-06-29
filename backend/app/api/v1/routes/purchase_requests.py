from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.auth.permissions import get_permission_codes, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.models.identity import User
from app.models.purchasing import PurchaseRequest, PurchaseRequestLineItem
from app.models.workflow import WorkflowInstance
from app.schemas.attachment import AttachmentCategory, AttachmentResponse
from app.schemas.flow import FlowInstanceResponse
from app.schemas.purchasing import (
    DraftExpirationResponse,
    PurchaseLineResponse,
    PurchaseLineWrite,
    PurchaseRequestCreate,
    PurchaseRequestResponse,
    PurchaseRequestUpdate,
    PurchaseValidationResult,
)
from app.services.attachment_service import (
    AttachmentError,
    attachment_path,
    delete_attachment,
    get_attachment,
    list_attachments,
    store_attachment,
)
from app.services.purchase_request_service import (
    PurchaseRequestError,
    add_line_item,
    clone_purchase_request,
    create_purchase_request,
    delete_line_item,
    expire_stale_drafts,
    submit_purchase_request,
    update_line_item,
    update_purchase_request,
    validate_purchase_request,
)
from app.services.purchasing_rule_service import seed_purchasing_defaults

router = APIRouter(prefix="/purchase-requests", tags=["purchase-requests"])


def _get_request(db: Session, request_id: str, user: User) -> PurchaseRequest:
    request = db.scalar(
        select(PurchaseRequest)
        .options(selectinload(PurchaseRequest.line_items))
        .where(PurchaseRequest.id == request_id)
    )
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Purchase request not found"
        )
    if request.created_by != user.email and "SYSTEM_ADMIN" not in {
        role.code for role in user.roles
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Purchase request access denied"
        )
    return request


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing required permission: {exc}"
        )
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("", response_model=PurchaseRequestResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: PurchaseRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PurchaseRequest:
    try:
        return create_purchase_request(db, payload, user.email)
    except PurchaseRequestError as exc:
        raise _translate_error(exc) from exc


@router.get("", response_model=list[PurchaseRequestResponse])
def list_all(
    request_status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PurchaseRequest]:
    statement = select(PurchaseRequest).options(selectinload(PurchaseRequest.line_items))
    if "SYSTEM_ADMIN" not in {role.code for role in user.roles}:
        statement = statement.where(PurchaseRequest.created_by == user.email)
    if request_status is not None:
        statement = statement.where(PurchaseRequest.status == request_status)
    return list(db.scalars(statement.order_by(PurchaseRequest.created_at.desc())).unique().all())


@router.post("/seed-defaults")
def seed_defaults(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("configuration.manage")),
) -> dict[str, int]:
    return {"seeded_count": seed_purchasing_defaults(db, user.email)}


@router.post("/drafts/expire", response_model=DraftExpirationResponse)
def expire_drafts(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("configuration.manage")),
) -> DraftExpirationResponse:
    return DraftExpirationResponse(expired_count=expire_stale_drafts(db, user.email))


@router.get("/{request_id}", response_model=PurchaseRequestResponse)
def get_one(
    request_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> PurchaseRequest:
    return _get_request(db, request_id, user)


@router.patch("/{request_id}", response_model=PurchaseRequestResponse)
def update(
    request_id: str,
    payload: PurchaseRequestUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PurchaseRequest:
    try:
        return update_purchase_request(db, _get_request(db, request_id, user), payload, user.email)
    except PurchaseRequestError as exc:
        raise _translate_error(exc) from exc


@router.get("/{request_id}/validation", response_model=PurchaseValidationResult)
def validate(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PurchaseValidationResult:
    evaluation = validate_purchase_request(db, _get_request(db, request_id, user))
    return PurchaseValidationResult(
        ready=evaluation.ready,
        errors=[issue.__dict__ for issue in evaluation.errors],
        warnings=[issue.__dict__ for issue in evaluation.warnings],
    )


@router.get("/{request_id}/workflow", response_model=FlowInstanceResponse)
def read_workflow(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkflowInstance:
    request = _get_request(db, request_id, user)
    if request.workflow_instance_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not started")
    instance = db.get(WorkflowInstance, request.workflow_instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return instance


@router.post("/{request_id}/clone", response_model=PurchaseRequestResponse)
def clone(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PurchaseRequest:
    try:
        return clone_purchase_request(db, _get_request(db, request_id, user), user.email)
    except PurchaseRequestError as exc:
        raise _translate_error(exc) from exc


@router.post(
    "/{request_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    request_id: str,
    category: AttachmentCategory = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttachmentResponse:
    request = _get_request(db, request_id, user)
    content = await file.read(settings.attachment_max_bytes + 1)
    try:
        attachment = store_attachment(
            db,
            request,
            file.filename or "attachment",
            file.content_type or "application/octet-stream",
            content,
            category,
            user.email,
            settings.attachment_storage_path,
            settings.attachment_max_bytes,
        )
    except AttachmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AttachmentResponse.model_validate(attachment)


@router.get("/{request_id}/attachments", response_model=list[AttachmentResponse])
def read_attachments(
    request_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AttachmentResponse]:
    request = _get_request(db, request_id, user)
    return [AttachmentResponse.model_validate(item) for item in list_attachments(db, request.id)]


@router.get("/{request_id}/attachments/{attachment_id}/content")
def download_attachment(
    request_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    request = _get_request(db, request_id, user)
    try:
        attachment = get_attachment(db, request.id, attachment_id)
        path = attachment_path(attachment, settings.attachment_storage_path)
    except AttachmentError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FileResponse(
        path, media_type=attachment.content_type, filename=attachment.original_filename
    )


@router.delete("/{request_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_attachment(
    request_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    request = _get_request(db, request_id, user)
    try:
        attachment = get_attachment(db, request.id, attachment_id)
        delete_attachment(db, request, attachment, user.email, settings.attachment_storage_path)
    except AttachmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    request_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    request = _get_request(db, request_id, user)
    if request.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft purchase requests can be deleted")
    db.delete(request)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{request_id}/line-items", response_model=PurchaseLineResponse)
def add_line(
    request_id: str,
    payload: PurchaseLineWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PurchaseRequestLineItem:
    try:
        return add_line_item(db, _get_request(db, request_id, user), payload, user.email)
    except PurchaseRequestError as exc:
        raise _translate_error(exc) from exc


@router.put("/{request_id}/line-items/{line_id}", response_model=PurchaseLineResponse)
def update_line(
    request_id: str,
    line_id: int,
    payload: PurchaseLineWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PurchaseRequestLineItem:
    request = _get_request(db, request_id, user)
    line = next((item for item in request.line_items if item.id == line_id), None)
    if line is None:
        raise HTTPException(status_code=404, detail="Line item not found")
    try:
        return update_line_item(db, request, line, payload, user.email)
    except PurchaseRequestError as exc:
        raise _translate_error(exc) from exc


@router.delete("/{request_id}/line-items/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_line(
    request_id: str,
    line_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    request = _get_request(db, request_id, user)
    line = next((item for item in request.line_items if item.id == line_id), None)
    if line is None:
        raise HTTPException(status_code=404, detail="Line item not found")
    try:
        delete_line_item(db, request, line, user.email)
    except PurchaseRequestError as exc:
        raise _translate_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{request_id}/submit", response_model=PurchaseRequestResponse)
def submit(
    request_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> PurchaseRequest:
    try:
        return submit_purchase_request(
            db, _get_request(db, request_id, user), user, get_permission_codes(user)
        )
    except (PurchaseRequestError, PermissionError) as exc:
        raise _translate_error(exc) from exc
