import csv
import io
import json
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.event_snapshot import EventSnapshot
from app.schemas.audit_reporting import AuditCountMetric, AuditEventPage, AuditSummaryResponse
from app.schemas.event_snapshot import EventSnapshotResponse


def _filtered_statement(
    statement: Select,
    *,
    event_type: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Select:
    if event_type is not None:
        statement = statement.where(EventSnapshot.event_type == event_type)
    if entity_type is not None:
        statement = statement.where(EventSnapshot.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(EventSnapshot.entity_id == entity_id)
    if actor is not None:
        statement = statement.where(EventSnapshot.actor == actor)
    if date_from is not None:
        statement = statement.where(EventSnapshot.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(EventSnapshot.created_at < date_to)
    return statement


def query_audit_events(
    db: Session, *, limit: int = 100, offset: int = 0, **filters
) -> AuditEventPage:
    count_statement = _filtered_statement(
        select(func.count()).select_from(EventSnapshot), **filters
    )
    event_statement = _filtered_statement(select(EventSnapshot), **filters)
    events = db.scalars(
        event_statement.order_by(EventSnapshot.created_at.desc(), EventSnapshot.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return AuditEventPage(
        items=[EventSnapshotResponse.model_validate(item) for item in events],
        total=int(db.scalar(count_statement) or 0),
        limit=limit,
        offset=offset,
    )


def _top_counts(db: Session, column, filters: dict) -> list[AuditCountMetric]:
    statement = _filtered_statement(
        select(column, func.count()).select_from(EventSnapshot), **filters
    )
    rows = db.execute(statement.group_by(column).order_by(func.count().desc(), column).limit(25))
    return [AuditCountMetric(key=str(key), count=int(count)) for key, count in rows]


def audit_summary(db: Session, **filters) -> AuditSummaryResponse:
    total = int(
        db.scalar(_filtered_statement(select(func.count()).select_from(EventSnapshot), **filters))
        or 0
    )
    return AuditSummaryResponse(
        total=total,
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
        event_types=_top_counts(db, EventSnapshot.event_type, filters),
        entity_types=_top_counts(db, EventSnapshot.entity_type, filters),
        actors=_top_counts(db, EventSnapshot.actor, filters),
    )


def _safe_csv_text(value: str) -> str:
    return f"'{value}" if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value


def export_audit_csv(db: Session, *, maximum_rows: int = 10000, **filters) -> bytes:
    statement = _filtered_statement(select(EventSnapshot), **filters)
    events = db.scalars(
        statement.order_by(EventSnapshot.created_at.desc(), EventSnapshot.id.desc()).limit(
            maximum_rows
        )
    ).all()
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        ["id", "created_at", "event_type", "entity_type", "entity_id", "actor", "payload"]
    )
    for item in events:
        writer.writerow(
            [
                item.id,
                item.created_at.isoformat(),
                _safe_csv_text(item.event_type),
                _safe_csv_text(item.entity_type),
                _safe_csv_text(item.entity_id),
                _safe_csv_text(item.actor),
                _safe_csv_text(json.dumps(item.payload, sort_keys=True, separators=(",", ":"))),
            ]
        )
    return stream.getvalue().encode("utf-8")
