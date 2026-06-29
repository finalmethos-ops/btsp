import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.event_snapshot import EventSnapshot
from app.models.identity import Permission, Role, User
from app.schemas.role_admin import RoleAdminCreate, RoleAdminUpdate
from app.services.role_admin_service import (
    RoleAdminError,
    create_role,
    delete_role,
    list_roles,
    update_role,
)


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Permission(code="analytics.read", description="Read analytics"),
                Permission(code="roles.manage", description="Manage roles"),
                Role(code="SYSTEM_ADMIN", name="System Administrator", is_system_role=True),
            ]
        )
        session.commit()
        yield session


def test_custom_role_lifecycle_is_audited(db: Session) -> None:
    created = create_role(
        db,
        RoleAdminCreate(
            code="REPORT_READER",
            name="Report Reader",
            permission_codes=["analytics.read"],
        ),
        "admin@example.com",
    )
    updated = update_role(
        db,
        created.code,
        RoleAdminUpdate(
            name="Report Manager",
            permission_codes=["analytics.read", "roles.manage"],
        ),
        "admin@example.com",
    )

    assert updated is not None
    assert updated.name == "Report Manager"
    assert updated.permission_codes == ["analytics.read", "roles.manage"]
    assert delete_role(db, created.code, "admin@example.com") is True
    assert [item.event_type for item in db.scalars(select(EventSnapshot)).all()] == [
        "admin.role.created",
        "admin.role.updated",
        "admin.role.deleted",
    ]


def test_system_and_assigned_roles_are_protected(db: Session) -> None:
    with pytest.raises(RoleAdminError, match="System roles"):
        update_role(
            db,
            "SYSTEM_ADMIN",
            RoleAdminUpdate(name="Changed"),
            "admin@example.com",
        )

    created = create_role(
        db,
        RoleAdminCreate(code="BUYER", name="Buyer", permission_codes=[]),
        "admin@example.com",
    )
    role = db.scalar(select(Role).where(Role.code == created.code))
    assert role is not None
    db.add(
        User(
            email="buyer@example.com",
            display_name="Buyer",
            password_hash="not-used",
            is_active=True,
            roles=[role],
        )
    )
    db.commit()

    assigned = next(item for item in list_roles(db) if item.code == "BUYER")
    assert assigned.user_count == 1
    with pytest.raises(RoleAdminError, match="Assigned roles"):
        delete_role(db, "BUYER", "admin@example.com")


def test_unknown_permissions_are_rejected(db: Session) -> None:
    with pytest.raises(RoleAdminError, match="Unknown permissions"):
        create_role(
            db,
            RoleAdminCreate(
                code="INVALID_ROLE",
                name="Invalid",
                permission_codes=["missing.permission"],
            ),
            "admin@example.com",
        )
