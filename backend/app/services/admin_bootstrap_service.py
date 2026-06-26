from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.identity import Permission, Role, User
from app.schemas.admin_bootstrap import AdminBootstrapRequest, AdminBootstrapResponse
from app.services.identity_defaults import CORE_PERMISSION_DEFINITIONS, CORE_ROLE_DEFINITIONS


def ensure_core_permissions(db: Session) -> dict[str, Permission]:
    permissions: dict[str, Permission] = {}
    for code, description in CORE_PERMISSION_DEFINITIONS.items():
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, description=description)
            db.add(permission)
        permissions[code] = permission
    db.flush()
    return permissions


def ensure_core_roles(db: Session, permissions: dict[str, Permission]) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for code, definition in CORE_ROLE_DEFINITIONS.items():
        role = db.scalar(select(Role).where(Role.code == code))
        if role is None:
            role = Role(
                code=code,
                name=str(definition["name"]),
                workflow_code=definition["workflow_code"],
                is_system_role=True,
            )
            db.add(role)
        role.permissions = [permissions[permission_code] for permission_code in definition["permissions"]]
        roles[code] = role
    db.flush()
    return roles


def bootstrap_admin_user(db: Session, payload: AdminBootstrapRequest) -> AdminBootstrapResponse:
    permissions = ensure_core_permissions(db)
    roles = ensure_core_roles(db, permissions)

    user = db.scalar(select(User).where(User.email == payload.email))
    created = False
    if user is None:
        user = User(
            email=payload.email,
            display_name=payload.display_name,
            password_hash=hash_password(payload.password),
            home_store_number=payload.home_store_number,
            region_code=payload.region_code,
            is_active=True,
        )
        db.add(user)
        created = True
    else:
        user.display_name = payload.display_name
        user.home_store_number = payload.home_store_number
        user.region_code = payload.region_code
        user.is_active = True

    user.roles = [roles["SYSTEM_ADMIN"]]
    db.commit()
    db.refresh(user)

    role_codes = sorted({role.code for role in user.roles})
    permission_codes = sorted({permission.code for role in user.roles for permission in role.permissions})
    return AdminBootstrapResponse(
        email=user.email,
        display_name=user.display_name,
        roles=role_codes,
        permissions=permission_codes,
        created=created,
    )
