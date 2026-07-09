from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crop import Diagnosis
from app.models.crop_stage import Crop, CropStage
from app.models.farm import Farm


class StageAdvisoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_crop_by_normalized_name(self, normalized_name: str) -> Crop | None:
        statement = select(Crop).where(
            Crop.normalized_name == normalized_name,
            Crop.is_active.is_(True),
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_generic_crop(self) -> Crop | None:
        return self.get_crop_by_normalized_name("generic")

    def list_crop_stages(self, crop_id: uuid.UUID) -> Sequence[CropStage]:
        statement = (
            select(CropStage)
            .where(CropStage.crop_id == crop_id)
            .order_by(CropStage.stage_order.asc())
        )
        return self.db.execute(statement).scalars().all()

    def get_latest_diagnosis_for_farm_user(
        self,
        *,
        farm_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Diagnosis | None:
        statement = (
            select(Diagnosis)
            .join(Farm, Diagnosis.farm_id == Farm.id)
            .where(Diagnosis.farm_id == farm_id, Farm.user_id == user_id)
            .order_by(Diagnosis.created_at.desc())
            .limit(1)
        )
        return self.db.execute(statement).scalar_one_or_none()
