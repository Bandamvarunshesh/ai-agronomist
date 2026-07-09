from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.timeline import TimelineEvent


class TimelineRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, event: TimelineEvent) -> TimelineEvent:
        self.db.add(event)
        return event

    def list_by_farm(
        self,
        farm_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[TimelineEvent]:
        statement = (
            select(TimelineEvent)
            .where(TimelineEvent.farm_id == farm_id)
            .order_by(TimelineEvent.event_date.desc(), TimelineEvent.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()
