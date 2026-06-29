from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.role_admin import (
    PermissionAdminResponse,
    RoleAdminCreate,
    RoleAdminResponse,
    RoleAdminUpdate,
)
from app.services.role_admin_service import (
    RoleAdminError,
    create_role,
    delete_role,
    list_permissions,
    list_roles,
    update_role,
)

router = APIRouter(prefix="/roles", tags=["role administration"])


@router.get("", response_model=list[RoleAdminResponse])
def read_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("roles.manage")),
) -> list[RoleAdminResponse]:
    return list_roles(db)


@router.get("/permissions", response_model=list[PermissionAdminResponse])
def read_permissions(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("roles.manage")),
) -> list[PermissionAdminResponse]:
    return [
        PermissionAdminResponse.model_validate(item, from_attributes=True)
        for item in list_permissions(db)
    ]


@router.post("", response_model=RoleAdminResponse, status_code=status.HTTP_201_CREATED)
def post_role(
    payload: RoleAdminCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("roles.manage")),
) -> RoleAdminResponse:
    try:
        return create_role(db, payload, user.email)
    except RoleAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{code}", response_model=RoleAdminResponse)
def patch_role(
    code: str,
    payload: RoleAdminUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("roles.manage")),
) -> RoleAdminResponse:
    try:
        role = update_role(db, code, payload, user.email)
    except RoleAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_role(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("roles.manage")),
) -> Response:
    try:
        deleted = delete_role(db, code, user.email)
    except RoleAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
