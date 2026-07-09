from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_active_user, get_notification_service
from app.models.user import User
from app.schemas.notification import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    NotificationRead,
)
from app.services.exceptions import (
    NotificationNotFoundError,
    NotificationPersistenceError,
)
from app.services.notification_service import NotificationService


router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationRead])
def get_notifications(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_active_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> list[NotificationRead]:
    try:
        return list(
            notification_service.list_notifications(
                user_id=current_user.id,
                skip=skip,
                limit=limit,
                unread_only=unread_only,
            )
        )
    except NotificationPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch notifications",
        )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationRead:
    try:
        return notification_service.mark_read(
            user_id=current_user.id,
            notification_id=notification_id,
        )
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    except NotificationPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to mark notification as read",
        )


@router.get(
    "/notification-preferences",
    response_model=NotificationPreferenceRead,
)
def get_notification_preferences(
    current_user: User = Depends(get_current_active_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationPreferenceRead:
    try:
        return notification_service.get_preferences(user_id=current_user.id)
    except NotificationPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch notification preferences",
        )


@router.put(
    "/notification-preferences",
    response_model=NotificationPreferenceRead,
)
def update_notification_preferences(
    preferences_in: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_active_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationPreferenceRead:
    try:
        return notification_service.update_preferences(
            user_id=current_user.id,
            preferences_in=preferences_in,
        )
    except NotificationPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update notification preferences",
        )
