import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.security import decode_access_token, hash_password
from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.catalog import CatalogVendor
from app.models.identity import Role, User, user_vendor_access
from app.schemas.user_admin import UserCreate, UserUpdate
from app.services.user_admin_service import create_user, update_user


def test_multi_vendor_login_requires_and_enforces_account_selection(
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
        vendors = [
            CatalogVendor(
                vendor_code="VENDOR-A",
                name="Vendor A",
                is_active=True,
                source_file="test.xlsx",
            ),
            CatalogVendor(
                vendor_code="VENDOR-B",
                name="Vendor B",
                is_active=True,
                source_file="test.xlsx",
            ),
            CatalogVendor(
                vendor_code="VENDOR-C",
                name="Vendor C",
                is_active=True,
                source_file="test.xlsx",
            ),
        ]
        vendor_user = User(
            email="representative@example.com",
            display_name="Vendor Representative",
            password_hash=hash_password("Vendor-Password!"),
            vendor_code="VENDOR-A",
            is_active=True,
            roles=[Role(code="VENDOR", name="Vendor", is_system_role=True)],
        )
        db.add_all([*vendors, vendor_user])
        db.flush()
        db.execute(
            insert(user_vendor_access),
            [
                {"user_id": vendor_user.id, "vendor_code": "VENDOR-A"},
                {"user_id": vendor_user.id, "vendor_code": "VENDOR-B"},
            ],
        )
        db.commit()

        def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        try:
            client = TestClient(app)
            login = client.post(
                "/api/v1/auth/login",
                json={
                    "email": vendor_user.email,
                    "password": "Vendor-Password!",
                    "login_context": "standard",
                },
            )
            assert login.status_code == 200
            initial_token = login.json()["access_token"]
            assert "active_vendor_code" not in decode_access_token(initial_token)

            initial_me = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {initial_token}"},
            )
            assert initial_me.status_code == 200
            assert initial_me.json()["vendor_code"] is None
            assert initial_me.json()["active_vendor_code"] is None
            assert initial_me.json()["vendor_accounts"] == [
                {"vendor_code": "VENDOR-A", "name": "Vendor A"},
                {"vendor_code": "VENDOR-B", "name": "Vendor B"},
            ]

            forbidden = client.post(
                "/api/v1/auth/vendor-context",
                headers={"Authorization": f"Bearer {initial_token}"},
                json={"vendor_code": "VENDOR-C"},
            )
            assert forbidden.status_code == 403

            selected = client.post(
                "/api/v1/auth/vendor-context",
                headers={"Authorization": f"Bearer {initial_token}"},
                json={"vendor_code": "VENDOR-B"},
            )
            assert selected.status_code == 200
            selected_token = selected.json()["access_token"]
            assert decode_access_token(selected_token)["active_vendor_code"] == "VENDOR-B"

            selected_me = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {selected_token}"},
            )
            assert selected_me.status_code == 200
            assert selected_me.json()["vendor_code"] == "VENDOR-B"
            assert selected_me.json()["active_vendor_code"] == "VENDOR-B"
        finally:
            app.dependency_overrides.pop(get_db, None)


def test_administrators_can_assign_and_update_multiple_vendor_accounts() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                CatalogVendor(
                    vendor_code="VENDOR-A",
                    name="Vendor A",
                    is_active=True,
                    source_file="test.xlsx",
                ),
                CatalogVendor(
                    vendor_code="VENDOR-B",
                    name="Vendor B",
                    is_active=True,
                    source_file="test.xlsx",
                ),
                Role(code="VENDOR", name="Vendor", is_system_role=True),
            ]
        )
        db.commit()

        created = create_user(
            db,
            UserCreate(
                email="representative@example.com",
                display_name="Vendor Representative",
                password="Vendor-Password!",
                role_codes=["VENDOR"],
                vendor_codes=["vendor-b", "vendor-a"],
            ),
        )
        assert created.vendor_codes == ["VENDOR-A", "VENDOR-B"]
        assert created.vendor_code == "VENDOR-A"

        updated = update_user(
            db,
            "representative@example.com",
            UserUpdate(vendor_codes=["VENDOR-B"]),
        )
        assert updated is not None
        assert updated.vendor_codes == ["VENDOR-B"]
        assert updated.vendor_code == "VENDOR-B"
