from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationPreference
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import (
    DEFAULT_ENABLED_NOTIFICATION_TYPES,
    NotificationPreferenceUpdate,
    SUPPORTED_NOTIFICATION_TYPES,
)
from app.services.exceptions import (
    NotificationNotFoundError,
    NotificationPersistenceError,
)


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = NotificationRepository(db)

    def list_notifications(
        self,
        *,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        unread_only: bool = False,
    ) -> Sequence[Notification]:
        try:
            return self.repository.list_by_user(
                user_id,
                skip=skip,
                limit=limit,
                unread_only=unread_only,
            )
        except SQLAlchemyError as exc:
            raise NotificationPersistenceError from exc

    def mark_read(
        self,
        *,
        user_id: uuid.UUID,
        notification_id: uuid.UUID,
    ) -> Notification:
        try:
            notification = self.repository.get_for_user(notification_id, user_id)
        except SQLAlchemyError as exc:
            raise NotificationPersistenceError from exc

        if notification is None:
            raise NotificationNotFoundError

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)

        return self._commit_and_refresh(notification)

    def get_preferences(self, *, user_id: uuid.UUID) -> NotificationPreference:
        preference = self._get_or_create_preference(user_id=user_id)
        try:
            self.db.commit()
            self.db.refresh(preference)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise NotificationPersistenceError from exc
        return preference

    def update_preferences(
        self,
        *,
        user_id: uuid.UUID,
        preferences_in: NotificationPreferenceUpdate,
    ) -> NotificationPreference:
        preference = self._get_or_create_preference(user_id=user_id)
        update_data = preferences_in.model_dump(exclude_unset=True)

        enabled_types = update_data.pop("enabled_types", None)
        if enabled_types is not None:
            preference.enabled_types = self._merge_enabled_types(
                preference.enabled_types,
                enabled_types,
            )

        for field, value in update_data.items():
            setattr(preference, field, value)

        return self._commit_and_refresh(preference)

    def add_notification(
        self,
        *,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        body: str,
        priority: str = "normal",
        farm_id: uuid.UUID | None = None,
        diagnosis_id: uuid.UUID | None = None,
        source: str = "system",
        payload: dict[str, Any] | None = None,
        dedupe_key: str | None = None,
        deep_link: str | None = None,
        scheduled_for: datetime | None = None,
        commit: bool = False,
    ) -> Notification | None:
        if notification_type not in SUPPORTED_NOTIFICATION_TYPES:
            raise NotificationPersistenceError(
                f"Unsupported notification type: {notification_type}",
            )

        try:
            if dedupe_key is not None:
                existing_notification = self.repository.get_by_dedupe_key(dedupe_key)
                if existing_notification is not None:
                    return existing_notification

            preference = self.repository.get_preference_by_user(user_id)
        except SQLAlchemyError as exc:
            raise NotificationPersistenceError from exc

        if not self._should_create_notification(
            preference=preference,
            notification_type=notification_type,
        ):
            return None

        channel = self._select_channel(preference)
        push_data = {
            "notification_type": notification_type,
            "farm_id": str(farm_id) if farm_id is not None else None,
            "diagnosis_id": str(diagnosis_id) if diagnosis_id is not None else None,
            "deep_link": deep_link,
            "source": source,
        }
        notification = Notification(
            user_id=user_id,
            farm_id=farm_id,
            diagnosis_id=diagnosis_id,
            notification_type=notification_type,
            title=title,
            body=body,
            priority=priority,
            channel=channel,
            scheduled_for=scheduled_for,
            payload=payload or {},
            source=source,
            dedupe_key=dedupe_key,
            deep_link=deep_link,
            push_title=title,
            push_body=body,
            push_data=push_data,
            delivery_status="pending",
        )
        self.repository.add(notification)

        if commit:
            return self._commit_and_refresh(notification)
        return notification

    def _get_or_create_preference(
        self,
        *,
        user_id: uuid.UUID,
    ) -> NotificationPreference:
        try:
            preference = self.repository.get_preference_by_user(user_id)
        except SQLAlchemyError as exc:
            raise NotificationPersistenceError from exc

        if preference is not None:
            preference.enabled_types = self._merge_enabled_types(
                preference.enabled_types,
                {},
            )
            return preference

        preference = NotificationPreference(
            user_id=user_id,
            enabled_types=dict(DEFAULT_ENABLED_NOTIFICATION_TYPES),
        )
        self.repository.add_preference(preference)
        return preference

    def _should_create_notification(
        self,
        *,
        preference: NotificationPreference | None,
        notification_type: str,
    ) -> bool:
        if preference is None:
            return True
        if not preference.notifications_enabled:
            return False
        if not self._select_channel(preference):
            return False

        enabled_types = self._merge_enabled_types(preference.enabled_types, {})
        return enabled_types.get(notification_type, True)

    def _select_channel(self, preference: NotificationPreference | None) -> str:
        if preference is None:
            return "in_app"
        if preference.in_app_enabled:
            return "in_app"
        if preference.push_enabled:
            return "push"
        if preference.email_enabled:
            return "email"
        if preference.sms_enabled:
            return "sms"
        return ""

    def _merge_enabled_types(
        self,
        current_types: dict[str, bool] | None,
        updates: dict[str, bool],
    ) -> dict[str, bool]:
        enabled_types = dict(DEFAULT_ENABLED_NOTIFICATION_TYPES)
        if current_types:
            enabled_types.update(
                {
                    key: bool(value)
                    for key, value in current_types.items()
                    if key in SUPPORTED_NOTIFICATION_TYPES
                }
            )
        enabled_types.update(updates)
        return enabled_types

    def _commit_and_refresh(self, model: Notification | NotificationPreference):
        try:
            self.db.commit()
            self.db.refresh(model)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise NotificationPersistenceError from exc
        return model
