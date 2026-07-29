from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_active_vendor_code,
    get_current_user,
    get_login_context,
)
from app.auth.security import hash_password, verify_password
from app.core.config import settings
from app.db.session import get_db
from app.models.catalog import CatalogVendor
from app.models.event_management import EventMembership, EventVendorBooth
from app.models.identity import User
from app.schemas.auth import (
    CurrentUserResponse,
    EventVendorContextRequest,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    RefreshTokenRequest,
    TokenResponse,
    VendorAccountResponse,
    VendorContextRequest,
)
from app.services.auth_rate_limit_service import (
    LoginRateLimitError,
    clear_login_attempts,
    register_login_attempt,
)
from app.services.auth_service import (
    authenticate_user,
    create_password_reset_token,
    create_session,
    issue_access_token,
    refresh_session,
    reset_password,
    revoke_session,
    user_permission_codes,
    user_role_codes,
    user_workflow_codes,
)
from app.services.vendor_access_service import (
    user_has_vendor_access,
    vendor_accounts_for_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _vendor_name_key(value: str | None) -> str:
    return "".join(character for character in (value or "").upper() if character.isalnum())


def _canonical_event_vendor_code(
    db: Session, user: User, event_id: str, requested_code: str
) -> str | None:
    """Resolve an event-only booth code to the user's canonical vendor account."""
    accounts = vendor_accounts_for_user(db, user)
    account_by_code = {account.vendor_code.upper(): account for account in accounts}
    direct = account_by_code.get(requested_code.upper())
    if direct is not None:
        return direct.vendor_code
    booth = db.scalar(
        select(EventVendorBooth).where(
            EventVendorBooth.event_id == event_id,
            EventVendorBooth.vendor_code == requested_code,
        )
    )
    if booth is None:
        return None
    event_vendor = db.scalar(
        select(CatalogVendor).where(CatalogVendor.vendor_code == booth.vendor_code)
    )
    event_name = _vendor_name_key(event_vendor.name if event_vendor else None)
    if not event_name:
        return None
    matches = [
        account
        for account in accounts
        if (account_name := _vendor_name_key(account.name))
        and (event_name == account_name or event_name in account_name or account_name in event_name)
    ]
    return matches[0].vendor_code if len(matches) == 1 else None


def _event_booth_code_for_vendor(
    db: Session, event_id: str, vendor_code: str, canonical_code: str | None
) -> str | None:
    exact = db.scalar(
        select(EventVendorBooth.vendor_code).where(
            EventVendorBooth.event_id == event_id,
            EventVendorBooth.vendor_code == vendor_code,
        )
    )
    if exact is not None:
        return exact
    if canonical_code is None:
        return None
    account = db.scalar(select(CatalogVendor).where(CatalogVendor.vendor_code == canonical_code))
    account_name = _vendor_name_key(account.name if account else None)
    if not account_name:
        return None
    booths = db.scalars(select(EventVendorBooth).where(EventVendorBooth.event_id == event_id)).all()
    matches = []
    for booth in booths:
        event_vendor = db.scalar(
            select(CatalogVendor).where(CatalogVendor.vendor_code == booth.vendor_code)
        )
        event_name = _vendor_name_key(event_vendor.name if event_vendor else None)
        if event_name and (
            event_name == account_name or event_name in account_name or account_name in event_name
        ):
            matches.append(booth.vendor_code)
    return matches[0] if len(matches) == 1 else None


def _token_response(
    db: Session, user: User, login_context: str, active_vendor_code: str | None = None
) -> TokenResponse:
    session, refresh_token = create_session(db, user, login_context, active_vendor_code)
    return TokenResponse(
        access_token=issue_access_token(
            user,
            login_context,
            active_vendor_code=active_vendor_code,
            session_id=session.id,
        ),
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    client_host = request.client.host if request.client is not None else "unknown"
    try:
        rate_limit_keys = register_login_attempt(payload.email, client_host)
    except LoginRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts; try again later",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    clear_login_attempts(rate_limit_keys)
    has_event_membership = (
        db.scalar(
            select(EventMembership.id).where(
                EventMembership.user_id == user.id,
                EventMembership.is_active.is_(True),
            )
        )
        is not None
    )
    if payload.login_context == "event" and not has_event_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not assigned to an event",
        )
    if payload.login_context == "standard" and not user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This event-only account must sign in through the event portal"
                if has_event_membership
                else "This account is not assigned to the standard portal"
            ),
        )
    vendor_accounts = (
        vendor_accounts_for_user(db, user) if payload.login_context == "standard" else []
    )
    active_vendor_code = vendor_accounts[0].vendor_code if len(vendor_accounts) == 1 else None
    return _token_response(db, user, payload.login_context, active_vendor_code)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    refreshed = refresh_session(db, payload.refresh_token)
    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    user, session = refreshed
    return _token_response(db, user, session.login_context, session.active_vendor_code)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> None:
    revoke_session(db, payload.refresh_token)


@router.post("/vendor-context", response_model=TokenResponse)
def select_vendor_context(
    payload: VendorContextRequest,
    current_user: User = Depends(get_current_user),
    login_context: str = Depends(get_login_context),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if login_context != "standard":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor account selection is only available in the standard portal",
        )
    if "VENDOR" not in user_role_codes(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not assigned to a vendor workspace",
        )
    if not user_has_vendor_access(db, current_user, payload.vendor_code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This vendor account is not assigned to your user",
        )
    vendor_accounts = vendor_accounts_for_user(db, current_user)
    if payload.vendor_code not in {account.vendor_code for account in vendor_accounts}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This vendor account is inactive or unavailable",
        )
    return _token_response(db, current_user, login_context, payload.vendor_code)


@router.post("/event-vendor-context", response_model=TokenResponse)
def select_event_vendor_context(
    payload: EventVendorContextRequest,
    current_user: User = Depends(get_current_user),
    login_context: str = Depends(get_login_context),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if login_context != "event":
        raise HTTPException(status_code=403, detail="Event vendor selection requires event login")
    membership = db.scalar(
        select(EventMembership).where(
            EventMembership.event_id == payload.event_id,
            EventMembership.user_id == current_user.id,
            EventMembership.membership_type == "vendor",
            EventMembership.is_active.is_(True),
        )
    )
    allowed_codes = set(membership.vendor_codes or []) if membership else set()
    if membership and membership.vendor_code:
        allowed_codes.add(membership.vendor_code)
    canonical_code = _canonical_event_vendor_code(
        db, current_user, payload.event_id, payload.vendor_code
    )
    booth_code = _event_booth_code_for_vendor(
        db, payload.event_id, payload.vendor_code, canonical_code
    )
    if (
        not membership
        or not ({payload.vendor_code, canonical_code, booth_code} & allowed_codes)
        or booth_code is None
        or canonical_code is None
    ):
        raise HTTPException(status_code=403, detail="Vendor is not approved for this event account")
    # Downstream catalog/order services must use the canonical account code,
    # while membership and booth records may retain the event-only alias.
    return _token_response(db, current_user, "event", canonical_code)


@router.post("/password-reset/request", response_model=PasswordResetResponse)
def request_password_reset(
    payload: PasswordResetRequest, db: Session = Depends(get_db)
) -> PasswordResetResponse:
    user = (
        db.query(User).filter(User.email == payload.email, User.is_active.is_(True)).one_or_none()
    )
    reset_token = create_password_reset_token(db, user) if user is not None else None
    # Local environments expose the token for development; production delivery is delegated
    # to the notification adapter and never returns credentials in the API response.
    if settings.environment.lower() == "local":
        return PasswordResetResponse(
            message="If the account exists, a reset link was created.", reset_token=reset_token
        )
    return PasswordResetResponse(message="If the account exists, a reset link was sent.")


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest, db: Session = Depends(get_db)
) -> None:
    if not reset_password(db, payload.token, payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        )


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.password_hash = hash_password(payload.new_password)
    current_user.password_change_required = False
    db.commit()


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
    login_context: str = Depends(get_login_context),
    active_vendor_code: str | None = Depends(get_active_vendor_code),
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    # Vendor attendees need their assigned account list in event context so
    # they can switch between vendors without leaving the event portal.
    vendor_accounts = (
        vendor_accounts_for_user(db, current_user)
        if login_context == "standard" or "VENDOR" in user_role_codes(current_user)
        else []
    )
    return CurrentUserResponse(
        email=current_user.email,
        display_name=current_user.display_name,
        roles=user_role_codes(current_user),
        permissions=user_permission_codes(current_user),
        workflows=user_workflow_codes(current_user),
        vendor_code=(active_vendor_code if vendor_accounts else current_user.vendor_code),
        active_vendor_code=active_vendor_code,
        vendor_accounts=[
            VendorAccountResponse(vendor_code=account.vendor_code, name=account.name)
            for account in vendor_accounts
        ],
        login_context=login_context,
        password_change_required=current_user.password_change_required,
    )
