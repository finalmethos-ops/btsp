from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.event_snapshot import EventSnapshot
from app.models.identity import Permission, Role, user_roles
from app.schemas.role_admin import RoleAdminCreate, RoleAdminResponse, RoleAdminUpdate


class RoleAdminError(ValueError):
    pass


def _permission_map(db: Session, codes: list[str]) -> dict[str, Permission]:
    permissions = {
        item.code: item
        for item in db.scalars(select(Permission).where(Permission.code.in_(codes))).all()
    }
    missing = sorted(set(codes) - permissions.keys())
    if missing:
        raise RoleAdminError(f"Unknown permissions: {', '.join(missing)}")
    return permissions


def _response(role: Role, user_count: int | None = None) -> RoleAdminResponse:
    return RoleAdminResponse(
        id=role.id,
        code=role.code,
        name=role.name,
        workflow_code=role.workflow_code,
        is_system_role=role.is_system_role,
        permission_codes=sorted(permission.code for permission in role.permissions),
        user_count=len(role.users) if user_count is None else user_count,
    )


def list_permissions(db: Session) -> list[Permission]:
    return list(db.scalars(select(Permission).order_by(Permission.code)).all())


def list_roles(db: Session) -> list[RoleAdminResponse]:
    counts = dict(
        db.execute(
            select(user_roles.c.role_id, func.count(user_roles.c.user_id)).group_by(
                user_roles.c.role_id
            )
        ).all()
    )
    roles = db.scalars(select(Role).order_by(Role.is_system_role.desc(), Role.code)).unique().all()
    return [_response(role, int(counts.get(role.id, 0))) for role in roles]


def create_role(db: Session, payload: RoleAdminCreate, actor: str) -> RoleAdminResponse:
    permissions = _permission_map(db, payload.permission_codes)
    role = Role(
        code=payload.code,
        name=payload.name,
        workflow_code=payload.workflow_code,
        is_system_role=False,
        permissions=[permissions[code] for code in payload.permission_codes],
    )
    db.add(role)
    try:
        db.flush()
        db.add(
            EventSnapshot(
                event_type="admin.role.created",
                entity_type="role",
                entity_id=role.code,
                actor=actor,
                payload={"permission_codes": sorted(payload.permission_codes)},
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RoleAdminError("Role code already exists") from exc
    db.refresh(role)
    return _response(role, 0)


def update_role(
    db: Session, code: str, payload: RoleAdminUpdate, actor: str
) -> RoleAdminResponse | None:
    role = db.scalar(select(Role).where(Role.code == code))
    if role is None:
        return None
    if role.is_system_role:
        raise RoleAdminError("System roles cannot be modified")
    values = payload.model_dump(exclude_unset=True)
    permission_codes = values.pop("permission_codes", None)
    if permission_codes is not None:
        permissions = _permission_map(db, permission_codes)
        role.permissions = [permissions[item] for item in permission_codes]
    for field, value in values.items():
        setattr(role, field, value)
    db.add(
        EventSnapshot(
            event_type="admin.role.updated",
            entity_type="role",
            entity_id=role.code,
            actor=actor,
            payload={
                "changed_fields": sorted(payload.model_fields_set),
                "permission_codes": sorted(permission.code for permission in role.permissions),
            },
        )
    )
    db.commit()
    db.refresh(role)
    return _response(role)


def delete_role(db: Session, code: str, actor: str) -> bool:
    role = db.scalar(select(Role).where(Role.code == code))
    if role is None:
        return False
    if role.is_system_role:
        raise RoleAdminError("System roles cannot be deleted")
    user_count = int(
        db.scalar(
            select(func.count()).select_from(user_roles).where(user_roles.c.role_id == role.id)
        )
        or 0
    )
    if user_count:
        raise RoleAdminError("Assigned roles cannot be deleted")
    db.add(
        EventSnapshot(
            event_type="admin.role.deleted",
            entity_type="role",
            entity_id=role.code,
            actor=actor,
            payload={"permission_codes": sorted(item.code for item in role.permissions)},
        )
    )
    db.delete(role)
    db.commit()
    return True
