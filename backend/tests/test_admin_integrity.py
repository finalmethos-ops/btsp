from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.event_snapshot import EventSnapshot
from app.models.identity import Permission, Role
from app.models.workflow import WorkflowDefinition
from app.services.identity_defaults import CORE_ROLE_DEFINITIONS
from scripts.validate_001w_integrity import ADMIN_PERMISSION_CODES, inspect_integrity


def _definition(version: int, *, active: bool) -> WorkflowDefinition:
    return WorkflowDefinition(
        code="BPP_PURCHASING",
        name="BPP Purchasing",
        version=version,
        states=["draft", "complete"],
        initial_state="draft",
        terminal_states=["complete"],
        transitions=[{"action": "complete", "source": "draft", "target": "complete"}],
        is_active=active,
    )


def test_administration_integrity_audit_accepts_seeded_invariants() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        permissions = [Permission(code=code, description=code) for code in ADMIN_PERMISSION_CODES]
        db.add_all(permissions)
        for code, definition in CORE_ROLE_DEFINITIONS.items():
            db.add(
                Role(
                    code=code,
                    name=str(definition["name"]),
                    is_system_role=True,
                    permissions=permissions if code == "SYSTEM_ADMIN" else [],
                )
            )
        db.add(_definition(1, active=True))
        db.add(
            EventSnapshot(
                event_type="admin.role.created",
                entity_type="role",
                entity_id="REPORT_READER",
                actor="admin@example.com",
                payload={},
            )
        )
        db.commit()

        result = inspect_integrity(db)

        assert result["missing_system_roles"] == []
        assert result["unexpected_system_roles"] == []
        assert result["missing_admin_permissions"] == []
        assert result["duplicate_active_workflows"] == []
        assert result["unattributed_admin_snapshot_ids"] == []


def test_administration_integrity_audit_reports_release_drift() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(code="SYSTEM_ADMIN", name="System Administrator", is_system_role=True))
        db.add(Role(code="UNMANAGED", name="Unmanaged", is_system_role=True))
        db.add_all([_definition(1, active=True), _definition(2, active=True)])
        db.add(
            EventSnapshot(
                event_type="admin.workflow.activation_changed",
                entity_type="workflow_definition",
                entity_id="BPP_PURCHASING:2",
                actor=" ",
                payload={},
            )
        )
        db.commit()

        result = inspect_integrity(db)

        assert result["missing_system_roles"]
        assert result["unexpected_system_roles"] == ["UNMANAGED"]
        assert result["missing_admin_permissions"] == sorted(ADMIN_PERMISSION_CODES)
        assert result["duplicate_active_workflows"] == [
            {"workflow_code": "BPP_PURCHASING", "active_definition_count": 2}
        ]
        assert len(result["unattributed_admin_snapshot_ids"]) == 1
