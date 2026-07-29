from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.security import hash_password
from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.identity import Permission, Role, User
from app.schemas.event_management import EventMembershipCreate, EventWrite
from app.services.event_management_service import add_membership, create_event


def test_login_context_separates_event_only_and_standard_accounts(
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
        platform_role = Role(
            code="TEST_PLATFORM",
            name="Test Platform User",
            is_system_role=False,
        )
        event_manager_permission = Permission(
            code="events.manage",
            description="Manage events",
        )
        store_loadout_read_permission = Permission(
            code="store_loadout.read",
            description="Read store loadout assignments",
        )
        event_manager_role = Role(
            code="TEST_EVENT_MANAGER",
            name="Test Event Manager",
            is_system_role=False,
            permissions=[event_manager_permission, store_loadout_read_permission],
        )
        platform_user = User(
            email="platform@example.com",
            display_name="Platform User",
            password_hash=hash_password("Platform-Password!"),
            is_active=True,
            roles=[platform_role],
        )
        registered_admin = User(
            email="registered.admin@example.com",
            display_name="Registered Admin",
            password_hash=hash_password("Registered-Admin-Password!"),
            is_active=True,
            roles=[event_manager_role],
        )
        db.add_all([platform_user, registered_admin])
        db.commit()
        event = create_event(
            db,
            EventWrite(
                name="Login Context Event",
                slug="login-context-event",
                starts_at=datetime(2027, 8, 1, 12, tzinfo=UTC),
                ends_at=datetime(2027, 8, 2, 12, tzinfo=UTC),
                venue_name="Test Hall",
                address_line1="1 Test Way",
                city="Orlando",
                state_code="FL",
                postal_code="32801",
            ),
            "admin@example.com",
        )
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email="event-only@example.com",
                display_name="Event Only User",
                password="Event-Only-Password!",
                membership_type="staff",
            ),
        )
        add_membership(
            db,
            event.id,
            EventMembershipCreate(
                email=registered_admin.email,
                display_name=registered_admin.display_name,
                membership_type="admin",
            ),
        )
        unregistered_event = create_event(
            db,
            EventWrite(
                name="Unregistered Admin Event",
                slug="unregistered-admin-event",
                starts_at=datetime(2027, 9, 1, 12, tzinfo=UTC),
                ends_at=datetime(2027, 9, 2, 12, tzinfo=UTC),
                venue_name="Other Hall",
                address_line1="2 Test Way",
                city="Orlando",
                state_code="FL",
                postal_code="32801",
            ),
            "admin@example.com",
        )

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        try:
            client = TestClient(app)
            event_only_standard = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "event-only@example.com",
                    "password": "Event-Only-Password!",
                    "login_context": "standard",
                },
            )
            assert event_only_standard.status_code == 403

            event_only_event = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "event-only@example.com",
                    "password": "Event-Only-Password!",
                    "login_context": "event",
                },
            )
            assert event_only_event.status_code == 200
            event_only_me = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {event_only_event.json()['access_token']}"},
            )
            assert event_only_me.json()["login_context"] == "event"

            registered_admin_event = client.post(
                "/api/v1/auth/login",
                json={
                    "email": registered_admin.email,
                    "password": "Registered-Admin-Password!",
                    "login_context": "event",
                },
            )
            assert registered_admin_event.status_code == 200
            registered_event_list = client.get(
                "/api/v1/events/mine",
                headers={
                    "Authorization": (f"Bearer {registered_admin_event.json()['access_token']}")
                },
            )
            assert [item["id"] for item in registered_event_list.json()] == [event.id]
            # Event-portal administration remains scoped to the signed-in
            # attendee; the standard admin workspace exposes the full roster.
            assert len(registered_event_list.json()[0]["memberships"]) == 1
            event_auth = {
                "Authorization": f"Bearer {registered_admin_event.json()['access_token']}"
            }
            registered_calendar = client.get(
                f"/api/v1/event-calendar/{event.id}",
                headers=event_auth,
            )
            assert registered_calendar.status_code == 200
            unregistered_calendar = client.get(
                f"/api/v1/event-calendar/{unregistered_event.id}",
                headers=event_auth,
            )
            assert unregistered_calendar.status_code == 403
            assert "not registered" in unregistered_calendar.json()["detail"]
            unregistered_loadout_assignments = client.get(
                f"/api/v1/store-loadout/events/{unregistered_event.id}/assignments",
                headers=event_auth,
            )
            assert unregistered_loadout_assignments.status_code == 403
            assert "not registered" in unregistered_loadout_assignments.json()["detail"]
            scoped_ordering_assignments = client.get(
                "/api/v1/event-ordering/assignments",
                headers=event_auth,
            )
            assert scoped_ordering_assignments.status_code == 200
            event_account_directory = client.get(
                "/api/v1/events/account-directory",
                headers=event_auth,
            )
            assert event_account_directory.status_code == 200
            assert set(event_account_directory.json()[0]) == {
                "id",
                "email",
                "display_name",
                "is_active",
                "vendor_codes",
            }
            blocked_platform_users = client.get(
                "/api/v1/users",
                headers=event_auth,
            )
            assert blocked_platform_users.status_code == 403
            assert "standard platform" in blocked_platform_users.json()["detail"]
            registered_admin_standard = client.post(
                "/api/v1/auth/login",
                json={
                    "email": registered_admin.email,
                    "password": "Registered-Admin-Password!",
                    "login_context": "standard",
                },
            )
            assert registered_admin_standard.status_code == 200
            standard_event_list = client.get(
                "/api/v1/events/mine",
                headers={
                    "Authorization": (f"Bearer {registered_admin_standard.json()['access_token']}")
                },
            )
            assert len(standard_event_list.json()) == 2

            platform_event = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "platform@example.com",
                    "password": "Platform-Password!",
                    "login_context": "event",
                },
            )
            assert platform_event.status_code == 403

            platform_standard = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "platform@example.com",
                    "password": "Platform-Password!",
                    "login_context": "standard",
                },
            )
            assert platform_standard.status_code == 200
            platform_me = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {platform_standard.json()['access_token']}"},
            )
            assert platform_me.json()["login_context"] == "standard"
        finally:
            app.dependency_overrides.pop(get_db, None)
