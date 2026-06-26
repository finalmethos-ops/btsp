from app.schemas.user_admin import UserCreate, UserUpdate


def test_user_create_accepts_role_codes() -> None:
    payload = UserCreate(
        email="manager@example.com",
        display_name="Store Manager",
        password="change-this-password",
        role_codes=["BPP_ADMIN"],
    )

    assert payload.role_codes == ["BPP_ADMIN"]
    assert payload.is_active is True


def test_user_update_can_assign_roles() -> None:
    payload = UserUpdate(role_codes=["INDEPENDENT_ADMIN"])

    assert payload.role_codes == ["INDEPENDENT_ADMIN"]
