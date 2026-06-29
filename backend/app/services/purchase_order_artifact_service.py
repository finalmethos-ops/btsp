import csv
import hashlib
import json
import os
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.purchase_order import PurchaseOrder, PurchaseOrderArtifact
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.purchase_order_artifact import PurchaseOrderArtifactFormat
from app.services.snapshot_service import append_snapshot

CONTENT_TYPES = {
    PurchaseOrderArtifactFormat.PDF: "application/pdf",
    PurchaseOrderArtifactFormat.CSV: "text/csv; charset=utf-8",
    PurchaseOrderArtifactFormat.JSON: "application/json",
}


class PurchaseOrderArtifactError(ValueError):
    pass


def _order_payload(order: PurchaseOrder) -> dict[str, Any]:
    return {
        "po_number": order.po_number,
        "workflow_code": order.workflow_code,
        "vendor_code": order.vendor_code,
        "status": order.status,
        "currency": order.currency,
        "subtotal": str(order.subtotal),
        "freight_total": str(order.freight_total),
        "tax_total": str(order.tax_total),
        "total": str(order.total),
        "source_requests": [
            {
                "purchase_request_id": source.purchase_request_id,
                "store_number": source.store_number,
            }
            for source in order.sources
        ],
        "lines": [
            {
                "source_request_id": line.source_request_id,
                "source_line_id": line.source_line_id,
                "store_number": line.store_number,
                "product_code": line.product_code,
                "product_name": line.product_name,
                "quantity": str(line.quantity),
                "unit_price": str(line.unit_price),
                "freight_amount": str(line.freight_amount),
                "tax_amount": str(line.tax_amount),
                "extended_amount": str(line.extended_amount),
                "notes": line.notes,
            }
            for line in order.lines
        ],
    }


def render_json(order: PurchaseOrder) -> bytes:
    return (json.dumps(_order_payload(order), indent=2, sort_keys=True) + "\n").encode()


def _spreadsheet_safe(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def render_csv(order: PurchaseOrder) -> bytes:
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerow(
        [
            "po_number",
            "workflow_code",
            "vendor_code",
            "store_number",
            "source_request_id",
            "source_line_id",
            "product_code",
            "product_name",
            "quantity",
            "unit_price",
            "freight_amount",
            "tax_amount",
            "extended_amount",
            "currency",
            "notes",
        ]
    )
    for line in order.lines:
        writer.writerow(
            [
                order.po_number,
                order.workflow_code,
                order.vendor_code,
                line.store_number,
                line.source_request_id,
                line.source_line_id,
                _spreadsheet_safe(line.product_code),
                _spreadsheet_safe(line.product_name),
                line.quantity,
                line.unit_price,
                line.freight_amount,
                line.tax_amount,
                line.extended_amount,
                order.currency,
                _spreadsheet_safe(line.notes or ""),
            ]
        )
    return stream.getvalue().encode("utf-8")


def _pdf_text(value: Any) -> str:
    return str(value).encode("latin-1", "replace").decode("latin-1")


def render_pdf(order: PurchaseOrder) -> bytes:
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=letter, invariant=1)
    width, height = letter

    def header() -> float:
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawString(40, height - 45, f"Purchase Order {order.po_number}")
        canvas.setFont("Helvetica", 9)
        canvas.drawString(40, height - 65, _pdf_text(f"Vendor: {order.vendor_code}"))
        canvas.drawString(300, height - 65, _pdf_text(f"Currency: {order.currency}"))
        canvas.line(40, height - 78, width - 40, height - 78)
        return height - 98

    y = header()
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(40, y, "Store / Product")
    canvas.drawRightString(390, y, "Quantity")
    canvas.drawRightString(465, y, "Unit")
    canvas.drawRightString(width - 40, y, "Extended")
    y -= 16
    canvas.setFont("Helvetica", 8)
    for line in order.lines:
        if y < 75:
            canvas.showPage()
            y = header()
            canvas.setFont("Helvetica", 8)
        description = _pdf_text(f"{line.store_number} / {line.product_code} - {line.product_name}")[
            :72
        ]
        canvas.drawString(40, y, description)
        canvas.drawRightString(390, y, str(line.quantity))
        canvas.drawRightString(465, y, str(line.unit_price))
        canvas.drawRightString(width - 40, y, str(line.extended_amount))
        y -= 14
    y = max(y - 12, 60)
    canvas.line(330, y + 10, width - 40, y + 10)
    for label, value in (
        ("Subtotal", order.subtotal),
        ("Freight", order.freight_total),
        ("Tax", order.tax_total),
        ("Total", order.total),
    ):
        canvas.drawString(360, y, label)
        canvas.drawRightString(width - 40, y, str(value))
        y -= 14
    canvas.save()
    return stream.getvalue()


def render_artifact(order: PurchaseOrder, artifact_format: PurchaseOrderArtifactFormat) -> bytes:
    if artifact_format is PurchaseOrderArtifactFormat.PDF:
        return render_pdf(order)
    if artifact_format is PurchaseOrderArtifactFormat.CSV:
        return render_csv(order)
    return render_json(order)


def artifact_path(artifact: PurchaseOrderArtifact, storage_root: str) -> Path:
    root = Path(storage_root).resolve()
    path = (root / artifact.stored_filename).resolve()
    if root not in path.parents or not path.is_file():
        raise PurchaseOrderArtifactError("Purchase order artifact content is unavailable")
    return path


def generate_artifact(
    db: Session,
    order: PurchaseOrder,
    artifact_format: PurchaseOrderArtifactFormat,
    actor: str,
    storage_root: str,
    version: int = 1,
) -> PurchaseOrderArtifact:
    existing = db.scalar(
        select(PurchaseOrderArtifact).where(
            PurchaseOrderArtifact.purchase_order_id == order.id,
            PurchaseOrderArtifact.artifact_format == artifact_format.value,
            PurchaseOrderArtifact.version == version,
        )
    )
    if existing is not None:
        artifact_path(existing, storage_root)
        return existing
    content = render_artifact(order, artifact_format)
    stored_filename = f"{order.id}/v{version}/{order.po_number}.{artifact_format.value}"
    root = Path(storage_root).resolve()
    destination = (root / stored_filename).resolve()
    if root not in destination.parents:
        raise PurchaseOrderArtifactError("Purchase order artifact path is invalid")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(content)
        os.replace(temporary, destination)
        artifact = PurchaseOrderArtifact(
            purchase_order_id=order.id,
            artifact_format=artifact_format.value,
            version=version,
            stored_filename=stored_filename,
            content_type=CONTENT_TYPES[artifact_format],
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            created_by=actor,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
    except Exception:
        db.rollback()
        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise
    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="purchase_order.artifact_created",
            entity_type="purchase_order",
            entity_id=order.id,
            actor=actor,
            payload={
                "artifact_id": artifact.id,
                "format": artifact.artifact_format,
                "version": artifact.version,
                "size_bytes": artifact.size_bytes,
                "sha256": artifact.sha256,
            },
        ),
    )
    return artifact


def list_artifacts(db: Session, order_id: str) -> list[PurchaseOrderArtifact]:
    return list(
        db.scalars(
            select(PurchaseOrderArtifact)
            .where(PurchaseOrderArtifact.purchase_order_id == order_id)
            .order_by(PurchaseOrderArtifact.artifact_format, PurchaseOrderArtifact.version)
        ).all()
    )


def get_artifact(db: Session, order_id: str, artifact_id: str) -> PurchaseOrderArtifact | None:
    return db.scalar(
        select(PurchaseOrderArtifact).where(
            PurchaseOrderArtifact.id == artifact_id,
            PurchaseOrderArtifact.purchase_order_id == order_id,
        )
    )
