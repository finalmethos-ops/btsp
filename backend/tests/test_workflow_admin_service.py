from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.event_snapshot import EventSnapshot
from app.models.workflow import WorkflowDefinition, WorkflowInstance
from app.services.workflow_admin_service import (
    WorkflowAdminError,
    list_workflow_definitions,
    set_workflow_activation,
)


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for version in (1, 2):
            session.add(
                WorkflowDefinition(
                    code="BPP_PURCHASING",
                    name="BPP Purchasing",
                    version=version,
                    states=["draft", "complete"],
                    initial_state="draft",
                    terminal_states=["complete"],
                    transitions=[{"action": "submit", "source": "draft", "target": "complete"}],
                    is_active=version == 1,
                )
            )
        session.add(
            WorkflowInstance(
                workflow_code="BPP_PURCHASING",
                workflow_version=1,
                entity_type="purchase_request",
                entity_id="request-1",
                current_state="draft",
                status="active",
                context={},
                started_by="buyer@example.com",
                updated_by="buyer@example.com",
                started_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        session.commit()
        yield session


def test_activation_promotes_one_version_without_altering_instances(db: Session) -> None:
    promoted = set_workflow_activation(db, "BPP_PURCHASING", 2, True, "admin@example.com")

    assert promoted is not None
    assert promoted.is_active is True
    assert promoted.active_instance_count == 0
    definitions = list_workflow_definitions(db)
    version_one = next(item for item in definitions if item.version == 1)
    assert version_one.is_active is False
    assert version_one.active_instance_count == 1
    instance = db.scalar(select(WorkflowInstance))
    assert instance is not None
    assert instance.workflow_version == 1
    snapshot = db.scalar(select(EventSnapshot))
    assert snapshot is not None
    assert snapshot.payload["superseded_versions"] == [1]


def test_deactivation_pauses_new_selection_but_preserves_definition(db: Session) -> None:
    result = set_workflow_activation(db, "BPP_PURCHASING", 1, False, "admin@example.com")

    assert result is not None
    assert result.is_active is False
    assert result.active_instance_count == 1


def test_unknown_workflow_registration_is_rejected(db: Session) -> None:
    with pytest.raises(WorkflowAdminError, match="not registered"):
        set_workflow_activation(db, "UNKNOWN", 1, True, "admin@example.com")
