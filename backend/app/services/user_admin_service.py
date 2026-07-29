from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.catalog import CatalogVendor
from app.models.identity import Role, User, user_vendor_access
from app.schemas.user_admin import UserAdminResponse, UserCreate, UserUpdate
from app.services.vendor_access_service import vendor_codes_for_user


def user_to_admin_response(db: Session, user: User) -> UserAdminResponse:
    role_codes = sorted({role.code for role in user.roles})
    permission_codes = sorted(
        {permission.code for role in user.roles for permission in role.permissions}
    )
    return UserAdminResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        home_store_number=user.home_store_number,
        region_code=user.region_code,
        entity_code=user.entity_code,
        vendor_code=user.vendor_code,
        vendor_codes=vendor_codes_for_user(db, user),
        is_active=user.is_active,
        password_change_required=user.password_change_required,
        roles=role_codes,
        permissions=permission_codes,
    )


def get_roles_by_code(db: Session, role_codes: list[str]) -> list[Role]:
    if not role_codes:
        return []
    roles = list(db.scalars(select(Role).where(Role.code.in_(role_codes))).all())
    missing = sorted(set(role_codes) - {role.code for role in roles})
    if missing:
        raise ValueError(f"Unknown roles: {', '.join(missing)}")
    return roles


def normalized_vendor_codes(
    vendor_codes: list[str] | None,
    legacy_vendor_code: str | None,
) -> list[str]:
    values = [*(vendor_codes or []), legacy_vendor_code or ""]
    return sorted({value.strip().upper() for value in values if value.strip()})


def validate_vendor_identity(
    db: Session,
    roles: list[Role],
    vendor_codes: list[str],
) -> None:
    if any(role.code == "VENDOR" for role in roles) and not vendor_codes:
        raise ValueError("Vendor role requires at least one vendor account")
    if not vendor_codes:
        return
    active_codes = set(
        db.scalars(
            select(CatalogVendor.vendor_code).where(
                CatalogVendor.vendor_code.in_(vendor_codes),
                CatalogVendor.is_active.is_(True),
            )
        ).all()
    )
    unavailable = sorted(set(vendor_codes) - active_codes)
    if unavailable:
        raise ValueError(f"Unknown or inactive vendor accounts: {', '.join(unavailable)}")


def set_vendor_access(db: Session, user: User, vendor_codes: list[str]) -> None:
    db.execute(delete(user_vendor_access).where(user_vendor_access.c.user_id == user.id))
    if vendor_codes:
        db.execute(
            insert(user_vendor_access),
            [{"user_id": user.id, "vendor_code": vendor_code} for vendor_code in vendor_codes],
        )
    # Retain a deterministic legacy/default value for integrations that have not
    # yet adopted token-scoped vendor context.
    user.vendor_code = vendor_codes[0] if vendor_codes else None


def list_users(db: Session) -> list[UserAdminResponse]:
    users = db.scalars(select(User).order_by(User.email)).unique().all()
    return [user_to_admin_response(db, user) for user in users]


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, payload: UserCreate) -> UserAdminResponse:
    existing = get_user_by_email(db, payload.email)
    if existing is not None:
        raise ValueError("User already exists")

    roles = get_roles_by_code(db, payload.role_codes)
    vendor_codes = normalized_vendor_codes(payload.vendor_codes, payload.vendor_code)
    validate_vendor_identity(db, roles, vendor_codes)
    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        home_store_number=payload.home_store_number,
        region_code=payload.region_code,
        entity_code=payload.entity_code,
        vendor_code=vendor_codes[0] if vendor_codes else None,
        is_active=payload.is_active,
        password_change_required=payload.password_change_required,
    )
    user.roles = roles
    db.add(user)
    db.flush()
    set_vendor_access(db, user, vendor_codes)
    db.commit()
    db.refresh(user)
    return user_to_admin_response(db, user)


def update_user(db: Session, email: str, payload: UserUpdate) -> UserAdminResponse | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None

    values = payload.model_dump(exclude_unset=True)
    password = values.pop("password", None)
    role_codes = values.pop("role_codes", None)
    payload_vendor_codes = values.pop("vendor_codes", None)
    roles = user.roles if role_codes is None else get_roles_by_code(db, role_codes)
    if payload_vendor_codes is not None:
        candidate_vendor_codes = normalized_vendor_codes(
            payload_vendor_codes,
            values.pop("vendor_code", None),
        )
    elif "vendor_code" in values:
        candidate_vendor_codes = normalized_vendor_codes(None, values.pop("vendor_code"))
    else:
        candidate_vendor_codes = vendor_codes_for_user(db, user)
    validate_vendor_identity(db, roles, candidate_vendor_codes)
    for field, value in values.items():
        setattr(user, field, value)
    if password is not None:
        user.password_hash = hash_password(password)
        user.password_change_required = True
    if role_codes is not None:
        user.roles = roles
    set_vendor_access(db, user, candidate_vendor_codes)

    db.commit()
    db.refresh(user)
    return user_to_admin_response(db, user)
