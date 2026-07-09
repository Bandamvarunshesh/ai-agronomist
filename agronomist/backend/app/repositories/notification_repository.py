from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationPreference


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, notification: Notification) -> Notification:
        self.db.add(notification)
        return notification

    def add_preference(
        self,
        preference: NotificationPreference,
    ) -> NotificationPreference:
        self.db.add(preference)
        return preference

    def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
        unread_only: bool = False,
    ) -> Sequence[Notification]:
        statement = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            statement = statement.where(Notification.is_read.is_(False))

        statement = (
            statement.order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def get_for_user(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification | None:
        statement = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_dedupe_key(
        self,
        dedupe_key: str,
    ) -> Notification | None:
        statement = select(Notification).where(Notification.dedupe_key == dedupe_key)
        return self.db.execute(statement).scalar_one_or_none()

    def get_preference_by_user(
        self,
        user_id: uuid.UUID,
    ) -> NotificationPreference | None:
        statement = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()
