from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.farm import Farm


class FarmRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, farm: Farm) -> Farm:
        self.db.add(farm)
        return farm

    def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Farm]:
        statement = (
            select(Farm)
            .where(Farm.user_id == user_id)
            .order_by(Farm.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def get_by_id_for_user(
        self,
        farm_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Farm | None:
        statement = select(Farm).where(
            Farm.id == farm_id,
            Farm.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def delete(self, farm: Farm) -> None:
        self.db.delete(farm)
