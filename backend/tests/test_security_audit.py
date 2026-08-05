import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.security import hash_password
from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.event_snapshot import EventSnapshot
from app.models.identity import Permission, Role, User
from app.schemas.user_admin import UserCreate, UserUpdate
from app.services.user_admin_service import create_user, remove_user, update_user


def test_login_attempts_create_correlated_privacy_conscious_audit_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret-key-with-at-least-32-bytes")
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        role = Role(code="AUDITED_USER", name="Audited User", is_system_role=False)
        user = User(
            email="audited@example.com",
            display_name="Audited User",
            password_hash=hash_password("Audited-Password!"),
            is_active=True,
            roles=[role],
        )
        db.add(user)
        db.commit()

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        try:
            client = TestClient(app)
            failed = client.post(
                "/api/v1/auth/login",
                headers={"X-Request-ID": "failed-login-audit"},
                json={
                    "email": "unknown@example.com",
                    "password": "Incorrect-Password!",
                    "login_context": "standard",
                },
            )
            succeeded = client.post(
                "/api/v1/auth/login",
                headers={"X-Request-ID": "successful-login-audit"},
                json={
                    "email": user.email,
                    "password": "Audited-Password!",
                    "login_context": "standard",
                },
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert failed.status_code == 401
        assert succeeded.status_code == 200
        snapshots = list(
            db.scalars(
                select(EventSnapshot)
                .where(EventSnapshot.event_type == "user.login")
                .order_by(EventSnapshot.id)
            ).all()
        )
        assert [item.payload["outcome"] for item in snapshots] == ["failed", "succeeded"]
        assert snapshots[0].actor == "anonymous"
        assert snapshots[0].entity_id.startswith("attempt:")
        assert snapshots[0].payload["request_id"] == "failed-login-audit"
        assert snapshots[1].actor == user.email
        assert snapshots[1].entity_id == str(user.id)
        assert snapshots[1].payload["request_id"] == "successful-login-audit"
        serialized = json.dumps([item.payload for item in snapshots])
        assert "unknown@example.com" not in serialized
        assert "Incorrect-Password!" not in serialized
        assert "testclient" not in serialized


def test_user_administration_records_actions_and_permission_changes() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        permission = Permission(code="reports.read", description="Read reports")
        role = Role(
            code="REPORT_READER",
            name="Report Reader",
            is_system_role=False,
            permissions=[permission],
        )
        db.add(role)
        db.commit()

        created = create_user(
            db,
            UserCreate(
                email="reader@example.com",
                display_name="Report Reader",
                password="Temporary-Password!",
                role_codes=[role.code],
            ),
            actor="admin@example.com",
        )
        updated = update_user(
            db,
            created.email,
            UserUpdate(role_codes=[]),
            actor="admin@example.com",
        )
        assert updated is not None
        user = db.scalar(select(User).where(User.id == created.id))
        assert user is not None
        remove_user(db, user, "admin@example.com")

        snapshots = list(
            db.scalars(
                select(EventSnapshot)
                .where(
                    EventSnapshot.event_type.in_(["administrative.action", "permission.changed"])
                )
                .order_by(EventSnapshot.id)
            ).all()
        )
        admin_actions = [
            item.payload["action"]
            for item in snapshots
            if item.event_type == "administrative.action"
        ]
        permission_actions = [
            item.payload["action"] for item in snapshots if item.event_type == "permission.changed"
        ]
        assert admin_actions == ["user.created", "user.updated", "user.deleted"]
        assert permission_actions == ["user.created", "user.updated", "user.deleted"]
        assert all(item.actor == "admin@example.com" for item in snapshots)
        assert "Temporary-Password!" not in json.dumps([item.payload for item in snapshots])
