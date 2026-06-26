from sqlalchemy.orm import Session

from app.auth.security import create_access_token, verify_password
from app.models.identity import User


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def issue_access_token(user: User) -> str:
    return create_access_token(subject=user.email)


def user_permission_codes(user: User) -> list[str]:
    return sorted({permission.code for role in user.roles for permission in role.permissions})


def user_role_codes(user: User) -> list[str]:
    return sorted({role.code for role in user.roles})


def user_workflow_codes(user: User) -> list[str]:
    return sorted({role.workflow_code for role in user.roles if role.workflow_code})
