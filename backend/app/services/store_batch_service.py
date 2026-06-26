from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.store import StoreUpsert
from app.schemas.store_batch import StoreBatchError, StoreBatchRequest, StoreBatchResult
from app.services.snapshot_service import append_snapshot
from app.services.store_service import upsert_store


def validate_store_row(row: StoreUpsert) -> str | None:
    if not row.store_number.strip():
        return "Store number is required"
    if not row.name.strip():
        return "Store name is required"
    if not row.region_code.strip():
        return "Region code is required"
    return None


def process_store_batch(db: Session, payload: StoreBatchRequest) -> StoreBatchResult:
    errors: list[StoreBatchError] = []
    upserted_rows = 0

    for row in payload.rows:
        validation_error = validate_store_row(row)
        if validation_error is not None:
            errors.append(
                StoreBatchError(
                    row_number=row.row_number,
                    store_number=row.store_number,
                    message=validation_error,
                )
            )
            continue

        row.source_system = payload.source_system
        upsert_store(db, row)
        upserted_rows += 1

    result = StoreBatchResult(
        source_system=payload.source_system,
        submitted_by=payload.submitted_by,
        processed_at=datetime.now(UTC),
        total_rows=len(payload.rows),
        upserted_rows=upserted_rows,
        failed_rows=len(errors),
        errors=errors,
    )

    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="store.batch.processed",
            entity_type="store_batch",
            entity_id=f"{payload.source_system}:{result.processed_at.isoformat()}",
            actor=payload.submitted_by,
            payload=result.model_dump(mode="json"),
        ),
    )
    return result
