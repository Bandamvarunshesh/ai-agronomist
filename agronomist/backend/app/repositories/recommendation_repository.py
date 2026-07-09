from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recommendation import FarmRecommendation


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, recommendation: FarmRecommendation) -> FarmRecommendation:
        self.db.add(recommendation)
        return recommendation

    def list_by_farm(
        self,
        farm_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[FarmRecommendation]:
        statement = (
            select(FarmRecommendation)
            .where(FarmRecommendation.farm_id == farm_id)
            .order_by(
                FarmRecommendation.generated_at.desc(),
                FarmRecommendation.created_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()
