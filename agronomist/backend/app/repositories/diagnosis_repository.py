from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crop import Diagnosis


class DiagnosisRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, diagnosis: Diagnosis) -> Diagnosis:
        self.db.add(diagnosis)
        return diagnosis

    def list_by_farm(
        self,
        farm_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Diagnosis]:
        statement = (
            select(Diagnosis)
            .where(Diagnosis.farm_id == farm_id)
            .order_by(Diagnosis.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()
