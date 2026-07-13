from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    AccountSettingsRead,
    AccountSettingsUpdate,
    AdminUserRead,
    PasswordChangeRequest,
    PasswordChangeResponse,
    UserProfileRead,
    UserProfileUpdate,
    UserRead,
)
from app.services.exceptions import (
    DuplicateUserError,
    InvalidCredentialsError,
    UserPersistenceError,
    UserValidationError,
)
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_active_user)) -> UserRead:
    return current_user


@router.patch("/me", response_model=UserRead)
def patch_current_user(
    profile_in: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UserRead:
    return _update_profile(
        profile_in=profile_in,
        current_user=current_user,
        db=db,
        error_detail="Unable to update current user",
    )


@router.get("/me/profile", response_model=UserProfileRead)
def read_current_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserProfileRead:
    return current_user


@router.put("/me/profile", response_model=UserProfileRead)
def update_current_profile(
    profile_in: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UserProfileRead:
    return _update_profile(
        profile_in=profile_in,
        current_user=current_user,
        db=db,
        error_detail="Unable to update profile",
    )


def _update_profile(
    *,
    profile_in: UserProfileUpdate,
    current_user: User,
    db: Session,
    error_detail: str,
) -> User:
    try:
        return UserService(db).update_profile(user=current_user, profile_in=profile_in)
    except DuplicateUserError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this phone number already exists",
        )
    except UserValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_validation_error_detail(exc),
        )
    except UserPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail,
        )


@router.get("/me/settings", response_model=AccountSettingsRead)
def read_current_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AccountSettingsRead:
    return UserService(db).get_settings(user=current_user)


@router.put("/me/settings", response_model=AccountSettingsRead)
def update_current_settings(
    settings_in: AccountSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AccountSettingsRead:
    try:
        return UserService(db).update_settings(user=current_user, settings_in=settings_in)
    except UserValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_validation_error_detail(exc),
        )
    except UserPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update settings",
        )


@router.post("/me/password", response_model=PasswordChangeResponse)
def change_current_password(
    password_in: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PasswordChangeResponse:
    try:
        UserService(db).change_password(
            user=current_user,
            current_password=password_in.current_password,
            new_password=password_in.new_password,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current password is incorrect",
        )
    except UserPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to change password",
        )
    return PasswordChangeResponse()


@router.get("/admin/users", response_model=list[AdminUserRead])
def list_admin_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[AdminUserRead]:
    del current_user
    try:
        return list(UserService(db).list_users(skip=skip, limit=limit))
    except UserPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch users",
        )


def _validation_error_detail(exc: Exception) -> list[dict[str, str | list[str]]]:
    return [{"loc": ["body"], "msg": str(exc), "type": "value_error"}]
