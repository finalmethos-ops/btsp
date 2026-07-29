from datetime import UTC, datetime

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.auth.security import decode_access_token
from app.db.session import get_db
from app.models.identity import AuthSession, User
from app.services.vendor_access_service import (
    user_has_vendor_access,
    vendor_codes_for_user,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if not isinstance(email, str):
            raise credentials_error
    except jwt.PyJWTError as exc:
        raise credentials_error from exc

    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).one_or_none()
    if user is None:
        raise credentials_error
    session_id = payload.get("sid")
    if isinstance(session_id, str):
        session = (
            db.query(AuthSession)
            .filter(AuthSession.id == session_id, AuthSession.user_id == user.id)
            .one_or_none()
        )
        expires_at = (
            session.expires_at.replace(tzinfo=UTC)
            if session and session.expires_at.tzinfo is None
            else (session.expires_at if session else None)
        )
        if session is None or session.revoked_at is not None or expires_at <= datetime.now(UTC):
            raise credentials_error
    active_vendor_code = payload.get("active_vendor_code")
    if active_vendor_code is not None:
        if not isinstance(active_vendor_code, str) or not user_has_vendor_access(
            db, user, active_vendor_code
        ):
            raise credentials_error
        # Scope legacy vendor services to the selected account for this request only.
        # This does not persist a different default vendor on the user record.
        set_committed_value(user, "vendor_code", active_vendor_code)
    elif len(vendor_codes_for_user(db, user)) > 1:
        # A multi-vendor session is deliberately unable to reach any legacy
        # vendor-scoped service until an account has been selected.
        set_committed_value(user, "vendor_code", None)
    return user


def get_login_context(token: str | None = Depends(optional_oauth2_scheme)) -> str:
    if token is None:
        return "standard"
    try:
        context = decode_access_token(token).get("login_context", "standard")
    except jwt.PyJWTError:
        return "standard"
    return context if context in {"standard", "event"} else "standard"


def get_active_vendor_code(
    token: str | None = Depends(optional_oauth2_scheme),
) -> str | None:
    if token is None:
        return None
    try:
        active_vendor_code = decode_access_token(token).get("active_vendor_code")
    except jwt.PyJWTError:
        return None
    return active_vendor_code if isinstance(active_vendor_code, str) else None
