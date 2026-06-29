import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attachment import PurchaseRequestAttachment
from app.models.purchasing import PurchaseRequest
from app.models.workflow import WorkflowInstance
from app.schemas.attachment import AttachmentCategory
from app.schemas.event_snapshot import EventSnapshotCreate
from app.services.snapshot_service import append_snapshot

ALLOWED_TYPES = {
    "application/pdf": (".pdf", b"%PDF-"),
    "image/png": (".png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": (".jpg", b"\xff\xd8\xff"),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (".xlsx", b"PK"),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (".docx", b"PK"),
}


class AttachmentError(ValueError):
    pass


def _safe_original_filename(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name.strip()
    if not name or name in {".", ".."} or "\x00" in name or len(name) > 255:
        raise AttachmentError("Attachment filename is invalid")
    return name


def _validate_content(content: bytes, content_type: str, max_bytes: int) -> str:
    if not content:
        raise AttachmentError("Attachment cannot be empty")
    if len(content) > max_bytes:
        raise AttachmentError(f"Attachment exceeds the {max_bytes}-byte limit")
    allowed = ALLOWED_TYPES.get(content_type)
    if allowed is None:
        raise AttachmentError("Attachment content type is not allowed")
    extension, signature = allowed
    if not content.startswith(signature):
        raise AttachmentError("Attachment content does not match its declared type")
    return extension


def _ensure_upload_allowed(db: Session, request: PurchaseRequest) -> None:
    if request.status == "draft":
        return
    if request.workflow_instance_id is not None:
        instance = db.get(WorkflowInstance, request.workflow_instance_id)
        if instance is not None and instance.status == "active":
            return
    raise AttachmentError("Attachments cannot be added to a closed purchase request")


def store_attachment(
    db: Session,
    request: PurchaseRequest,
    filename: str,
    content_type: str,
    content: bytes,
    category: AttachmentCategory,
    actor: str,
    storage_root: str,
    max_bytes: int,
) -> PurchaseRequestAttachment:
    _ensure_upload_allowed(db, request)
    original_filename = _safe_original_filename(filename)
    extension = _validate_content(content, content_type, max_bytes)
    attachment_id = str(uuid4())
    stored_filename = f"{request.id}/{attachment_id}{extension}"
    root = Path(storage_root).resolve()
    destination = (root / stored_filename).resolve()
    if root not in destination.parents:
        raise AttachmentError("Attachment storage path is invalid")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
        os.replace(temporary, destination)
        attachment = PurchaseRequestAttachment(
            id=attachment_id,
            purchase_request_id=request.id,
            category=category.value,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            uploaded_by=actor,
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)
    except Exception:
        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        db.rollback()
        raise
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="purchase_request.attachment_added",
            entity_type="purchase_request",
            entity_id=request.id,
            actor=actor,
            payload={
                "attachment_id": attachment.id,
                "category": attachment.category,
                "filename": attachment.original_filename,
                "content_type": attachment.content_type,
                "size_bytes": attachment.size_bytes,
                "sha256": attachment.sha256,
            },
        ),
    )
    return attachment


def list_attachments(db: Session, request_id: str) -> list[PurchaseRequestAttachment]:
    return list(
        db.scalars(
            select(PurchaseRequestAttachment)
            .where(
                PurchaseRequestAttachment.purchase_request_id == request_id,
                PurchaseRequestAttachment.is_deleted.is_(False),
            )
            .order_by(PurchaseRequestAttachment.created_at)
        ).all()
    )


def get_attachment(db: Session, request_id: str, attachment_id: str) -> PurchaseRequestAttachment:
    attachment = db.scalar(
        select(PurchaseRequestAttachment).where(
            PurchaseRequestAttachment.id == attachment_id,
            PurchaseRequestAttachment.purchase_request_id == request_id,
            PurchaseRequestAttachment.is_deleted.is_(False),
        )
    )
    if attachment is None:
        raise AttachmentError("Attachment not found")
    return attachment


def attachment_path(attachment: PurchaseRequestAttachment, storage_root: str) -> Path:
    root = Path(storage_root).resolve()
    path = (root / attachment.stored_filename).resolve()
    if root not in path.parents or not path.is_file():
        raise AttachmentError("Attachment content is unavailable")
    return path


def delete_attachment(
    db: Session,
    request: PurchaseRequest,
    attachment: PurchaseRequestAttachment,
    actor: str,
    storage_root: str,
) -> None:
    if request.status != "draft":
        raise AttachmentError("Only draft attachments can be deleted")
    path = attachment_path(attachment, storage_root)
    attachment.is_deleted = True
    attachment.deleted_at = datetime.now(UTC)
    attachment.deleted_by = actor
    db.commit()
    path.unlink(missing_ok=True)
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="purchase_request.attachment_deleted",
            entity_type="purchase_request",
            entity_id=request.id,
            actor=actor,
            payload={"attachment_id": attachment.id, "sha256": attachment.sha256},
        ),
    )
