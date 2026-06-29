import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.event_snapshot import EventSnapshot
from app.models.identity import Role
from app.models.workflow import WorkflowDefinition
from app.services.identity_defaults import CORE_ROLE_DEFINITIONS

ADMIN_PERMISSION_CODES = {
    "audit.export",
    "configuration.manage",
    "notifications.manage",
    "roles.manage",
    "snapshots.read",
    "system.admin",
    "system.health.read",
    "workflows.manage",
}


def inspect_integrity(db: Session) -> dict[str, Any]:
    system_roles = {
        role.code: role
        for role in (db.scalars(select(Role).where(Role.is_system_role.is_(True))).unique().all())
    }
    expected_system_roles = set(CORE_ROLE_DEFINITIONS)
    missing_system_roles = sorted(expected_system_roles - system_roles.keys())
    unexpected_system_roles = sorted(system_roles.keys() - expected_system_roles)

    system_admin = system_roles.get("SYSTEM_ADMIN")
    system_admin_permissions = (
        {permission.code for permission in system_admin.permissions}
        if system_admin is not None
        else set()
    )
    missing_admin_permissions = sorted(ADMIN_PERMISSION_CODES - system_admin_permissions)

    duplicate_active_workflows = [
        {"workflow_code": code, "active_definition_count": int(count)}
        for code, count in db.execute(
            select(WorkflowDefinition.code, func.count(WorkflowDefinition.id))
            .where(WorkflowDefinition.is_active.is_(True))
            .group_by(WorkflowDefinition.code)
            .having(func.count(WorkflowDefinition.id) > 1)
            .order_by(WorkflowDefinition.code)
        ).all()
    ]
    unattributed_admin_snapshot_ids = list(
        db.scalars(
            select(EventSnapshot.id)
            .where(
                EventSnapshot.event_type.like("admin.%"),
                func.length(func.trim(EventSnapshot.actor)) == 0,
            )
            .order_by(EventSnapshot.id)
        ).all()
    )

    return {
        "missing_system_roles": missing_system_roles,
        "unexpected_system_roles": unexpected_system_roles,
        "missing_admin_permissions": missing_admin_permissions,
        "duplicate_active_workflows": duplicate_active_workflows,
        "unattributed_admin_snapshot_ids": unattributed_admin_snapshot_ids,
        "system_role_count": len(system_roles),
    }


def main() -> None:
    with SessionLocal() as db:
        result = inspect_integrity(db)
        assert not result["missing_system_roles"], "Required system roles are missing"
        assert not result["unexpected_system_roles"], "Unknown roles are marked as system roles"
        assert not result[
            "missing_admin_permissions"
        ], "SYSTEM_ADMIN is missing administration permissions"
        assert not result[
            "duplicate_active_workflows"
        ], "More than one workflow definition version is active"
        assert not result[
            "unattributed_admin_snapshot_ids"
        ], "Administrative audit snapshots are missing actor attribution"
        result["status"] = "ok"
        print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
