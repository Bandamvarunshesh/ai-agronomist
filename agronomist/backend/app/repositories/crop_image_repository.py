from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crop import CropImage


class CropImageRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, crop_image: CropImage) -> CropImage:
        self.db.add(crop_image)
        return crop_image

    def list_by_farm(
        self,
        farm_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[CropImage]:
        statement = (
            select(CropImage)
            .where(CropImage.farm_id == farm_id)
            .order_by(CropImage.uploaded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()
