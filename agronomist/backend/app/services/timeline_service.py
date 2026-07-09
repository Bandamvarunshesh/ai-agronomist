from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.timeline import TimelineEvent
from app.repositories.timeline_repository import TimelineRepository
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    TimelinePersistenceError,
)
from app.services.farm_service import FarmService


class TimelineService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = TimelineRepository(db)
        self.farm_service = FarmService(db)

    def list_events(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[TimelineEvent]:
        self._ensure_farm_owner(user_id, farm_id)
        try:
            return self.repository.list_by_farm(farm_id, skip=skip, limit=limit)
        except SQLAlchemyError as exc:
            raise TimelinePersistenceError from exc

    def add_event(
        self,
        *,
        farm_id: uuid.UUID,
        user_id: uuid.UUID | None,
        event_type: str,
        title: str,
        description: str | None = None,
        source: str = "system",
        payload: dict[str, Any] | None = None,
        event_date: date | None = None,
    ) -> TimelineEvent:
        event = TimelineEvent(
            farm_id=farm_id,
            user_id=user_id,
            event_type=event_type,
            title=title,
            description=description,
            event_date=event_date or date.today(),
            source=source,
            payload=payload or {},
        )
        return self.repository.add(event)

    def create_event(
        self,
        *,
        farm_id: uuid.UUID,
        user_id: uuid.UUID | None,
        event_type: str,
        title: str,
        description: str | None = None,
        source: str = "system",
        payload: dict[str, Any] | None = None,
        event_date: date | None = None,
    ) -> TimelineEvent:
        event = self.add_event(
            farm_id=farm_id,
            user_id=user_id,
            event_type=event_type,
            title=title,
            description=description,
            source=source,
            payload=payload,
            event_date=event_date,
        )
        try:
            self.db.commit()
            self.db.refresh(event)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise TimelinePersistenceError from exc
        return event

    def _ensure_farm_owner(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> None:
        try:
            self.farm_service.get_farm(user_id, farm_id)
        except FarmNotFoundError:
            raise
        except FarmPersistenceError as exc:
            raise TimelinePersistenceError from exc
