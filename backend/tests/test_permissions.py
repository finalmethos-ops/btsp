from types import SimpleNamespace

from app.auth.permissions import get_permission_codes, user_has_permission


def test_get_permission_codes_collects_role_permissions() -> None:
    permission = SimpleNamespace(code="stores.manage")
    role = SimpleNamespace(permissions=[permission])
    user = SimpleNamespace(roles=[role])

    assert get_permission_codes(user) == {"stores.manage"}


def test_user_has_permission_returns_false_when_missing() -> None:
    user = SimpleNamespace(roles=[])

    assert user_has_permission(user, "system.admin") is False
