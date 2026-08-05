from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.models.identity import AuthSession, PasswordResetToken, User


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).one_or_none()
    if user is None:
        return None
    now = datetime.now(UTC)
    if user.locked_until is not None and user.locked_until > now:
        return None
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.login_lockout_threshold:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_attempts = 0
        db.commit()
        return None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return user


def issue_access_token(
    user: User,
    login_context: str = "standard",
    active_vendor_code: str | None = None,
    session_id: str | None = None,
) -> str:
    return create_access_token(
        subject=user.email,
        login_context=login_context,
        active_vendor_code=active_vendor_code,
        session_id=session_id,
    )


def _hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def create_session(
    db: Session,
    user: User,
    login_context: str,
    active_vendor_code: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[AuthSession, str]:
    raw_refresh_token = token_urlsafe(48)
    session = AuthSession(
        id=str(uuid4()),
        user_id=user.id,
        refresh_token_hash=_hash_token(raw_refresh_token),
        login_context=login_context,
        active_vendor_code=active_vendor_code,
        expires_at=expires_at
        if expires_at is not None
        else datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()
    return session, raw_refresh_token


def refresh_session(db: Session, refresh_token: str) -> tuple[User, AuthSession] | None:
    session = (
        db.query(AuthSession)
        .filter(AuthSession.refresh_token_hash == _hash_token(refresh_token))
        .one_or_none()
    )
    now = datetime.now(UTC)
    expires_at = (
        session.expires_at.replace(tzinfo=UTC)
        if session and session.expires_at.tzinfo is None
        else (session.expires_at if session else None)
    )
    if session is None or session.revoked_at is not None or expires_at <= now:
        return None
    user = db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).one_or_none()
    if user is None:
        return None
    session.last_used_at = now
    db.commit()
    return user, session


def revoke_session(db: Session, refresh_token: str) -> None:
    session = (
        db.query(AuthSession)
        .filter(AuthSession.refresh_token_hash == _hash_token(refresh_token))
        .one_or_none()
    )
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.commit()


def create_password_reset_token(db: Session, user: User) -> str:
    raw_token = token_urlsafe(48)
    db.add(
        PasswordResetToken(
            id=str(uuid4()),
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(UTC)
            + timedelta(minutes=settings.password_reset_expire_minutes),
        )
    )
    db.commit()
    return raw_token


def reset_password(db: Session, raw_token: str, new_password: str) -> bool:
    token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == _hash_token(raw_token))
        .one_or_none()
    )
    now = datetime.now(UTC)
    expires_at = (
        token.expires_at.replace(tzinfo=UTC)
        if token and token.expires_at.tzinfo is None
        else (token.expires_at if token else None)
    )
    if token is None or token.used_at is not None or expires_at <= now:
        return False
    user = db.query(User).filter(User.id == token.user_id, User.is_active.is_(True)).one_or_none()
    if user is None:
        return False
    user.password_hash = hash_password(new_password)
    user.password_change_required = False
    user.failed_login_attempts = 0
    user.locked_until = None
    token.used_at = now
    db.query(AuthSession).filter(
        AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)
    ).update({AuthSession.revoked_at: now}, synchronize_session=False)
    db.commit()
    return True


def user_permission_codes(user: User) -> list[str]:
    return sorted({permission.code for role in user.roles for permission in role.permissions})


def user_role_codes(user: User) -> list[str]:
    return sorted({role.code for role in user.roles})


def user_workflow_codes(user: User) -> list[str]:
    return sorted({role.workflow_code for role in user.roles if role.workflow_code})
