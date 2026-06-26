from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.identity import Role, User
from app.schemas.user_admin import UserAdminResponse, UserCreate, UserUpdate


def user_to_admin_response(user: User) -> UserAdminResponse:
    role_codes = sorted({role.code for role in user.roles})
    permission_codes = sorted({permission.code for role in user.roles for permission in role.permissions})
    return UserAdminResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        home_store_number=user.home_store_number,
        region_code=user.region_code,
        is_active=user.is_active,
        roles=role_codes,
        permissions=permission_codes,
    )


def get_roles_by_code(db: Session, role_codes: list[str]) -> list[Role]:
    if not role_codes:
        return []
    return list(db.scalars(select(Role).where(Role.code.in_(role_codes))).all())


def list_users(db: Session) -> list[UserAdminResponse]:
    users = db.scalars(select(User).order_by(User.email)).unique().all()
    return [user_to_admin_response(user) for user in users]


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, payload: UserCreate) -> UserAdminResponse:
    existing = get_user_by_email(db, payload.email)
    if existing is not None:
        raise ValueError("User already exists")

    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        home_store_number=payload.home_store_number,
        region_code=payload.region_code,
        is_active=payload.is_active,
    )
    user.roles = get_roles_by_code(db, payload.role_codes)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_admin_response(user)


def update_user(db: Session, email: str, payload: UserUpdate) -> UserAdminResponse | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None

    values = payload.model_dump(exclude_unset=True)
    role_codes = values.pop("role_codes", None)
    for field, value in values.items():
        setattr(user, field, value)
    if role_codes is not None:
        user.roles = get_roles_by_code(db, role_codes)

    db.commit()
    db.refresh(user)
    return user_to_admin_response(user)
