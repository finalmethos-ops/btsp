from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.user_admin import UserAdminResponse, UserCreate, UserUpdate
from app.services.user_admin_service import create_user, list_users, update_user

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
    _current_user: User = Depends(require_permission("system.admin")),
) -> UserAdminResponse:
    try:
        return create_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{email}", response_model=UserAdminResponse)
def patch_user(
    email: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("system.admin")),
) -> UserAdminResponse:
    user = update_user(db, email, payload)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
