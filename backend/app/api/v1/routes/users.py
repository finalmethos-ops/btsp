from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.user_admin import UserAdminResponse, UserCreate, UserUpdate
from app.services.user_admin_service import (
    create_user,
    get_user_by_email,
    list_users,
    remove_user,
    update_user,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserAdminResponse])
def read_users(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("system.admin")),
) -> list[UserAdminResponse]:
    return list_users(db)


@router.post("", response_model=UserAdminResponse)
def write_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
) -> UserAdminResponse:
    try:
        return create_user(db, payload, current_user.email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{email}", response_model=UserAdminResponse)
def patch_user(
    email: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
) -> UserAdminResponse:
    try:
        user = update_user(db, email, payload, current_user.email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{email}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("system.admin")),
) -> None:
    user = get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="You cannot delete your own account"
        )
    remove_user(db, user, current_user.email)
