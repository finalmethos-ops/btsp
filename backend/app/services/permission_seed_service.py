from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import Permission, Role


def seed_permissions_for_roles(
    db: Session,
    definitions: dict[str, str],
    role_permission_codes: dict[str, set[str]],
) -> dict[str, Permission]:
    permissions: dict[str, Permission] = {}
    for code, description in definitions.items():
        permission = db.scalar(select(Permission).where(Permission.code == code))
        if permission is None:
            permission = Permission(code=code, description=description)
            db.add(permission)
        else:
            permission.description = description
        permissions[code] = permission
    db.flush()

    roles = db.scalars(select(Role).where(Role.code.in_(role_permission_codes))).all()
    for role in roles:
        assigned = {permission.code: permission for permission in role.permissions}
        for code in role_permission_codes[role.code]:
            assigned[code] = permissions[code]
        role.permissions = list(assigned.values())
    db.commit()
    return permissions
