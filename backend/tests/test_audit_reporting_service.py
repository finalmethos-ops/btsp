from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.event_snapshot import EventSnapshot
from app.services.audit_reporting_service import (
    audit_summary,
    export_audit_csv,
    query_audit_events,
)


def test_audit_reporting_filters_pages_summarizes_and_escapes_csv() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    started = datetime(2026, 6, 1, tzinfo=UTC)
    with Session(engine) as db:
        db.add_all(
            [
                EventSnapshot(
                    event_type="admin.role.created",
                    entity_type="role",
                    entity_id="BUYER",
                    actor="admin@example.com",
                    payload={"permissions": 2},
                    created_at=started,
                ),
                EventSnapshot(
                    event_type="workflow.started",
                    entity_type="purchase_request",
                    entity_id="=FORMULA()",
                    actor="buyer@example.com",
                    payload={"state": "draft"},
                    created_at=started + timedelta(hours=1),
                ),
                EventSnapshot(
                    event_type="workflow.advanced",
                    entity_type="purchase_request",
                    entity_id="PR-2",
                    actor="admin@example.com",
                    payload={"state": "approved"},
                    created_at=started + timedelta(hours=2),
                ),
            ]
        )
        db.commit()

        page = query_audit_events(db, actor="admin@example.com", limit=1, offset=0)
        summary = audit_summary(db, date_from=started, date_to=started + timedelta(days=1))
        content = export_audit_csv(db, entity_type="purchase_request")

        assert page.total == 2
        assert len(page.items) == 1
        assert page.items[0].event_type == "workflow.advanced"
        assert summary.total == 3
        assert summary.entity_types[0].key == "purchase_request"
        assert summary.entity_types[0].count == 2
        assert b"'=FORMULA()" in content
        assert content.startswith(b"id,created_at,event_type")
