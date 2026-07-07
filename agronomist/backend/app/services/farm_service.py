from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.farm import Farm
from app.repositories.farm_repository import FarmRepository
from app.schemas.farm import FarmCreate, FarmUpdate
from app.services.exceptions import FarmNotFoundError, FarmPersistenceError


class FarmService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = FarmRepository(db)

    def create_farm(self, user_id: uuid.UUID, farm_in: FarmCreate) -> Farm:
        farm = Farm(user_id=user_id, **farm_in.model_dump())
        self.repository.add(farm)
        return self._commit_and_refresh(farm)

    def list_farms(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Farm]:
        try:
            return self.repository.list_by_user(user_id, skip=skip, limit=limit)
        except SQLAlchemyError as exc:
            raise FarmPersistenceError from exc

    def get_farm(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> Farm:
        try:
            farm = self.repository.get_by_id_for_user(farm_id, user_id)
        except SQLAlchemyError as exc:
            raise FarmPersistenceError from exc

        if farm is None:
            raise FarmNotFoundError
        return farm

    def update_farm(
        self,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        farm_in: FarmUpdate,
    ) -> Farm:
        farm = self.get_farm(user_id, farm_id)
        update_data = farm_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(farm, field, value)

        return self._commit_and_refresh(farm)

    def delete_farm(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> None:
        farm = self.get_farm(user_id, farm_id)
        self.repository.delete(farm)
        self._commit()

    def _commit_and_refresh(self, farm: Farm) -> Farm:
        self._commit()
        self.db.refresh(farm)
        return farm

    def _commit(self) -> None:
        try:
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise FarmPersistenceError from exc
