from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.crop import CropImage, Diagnosis
from app.repositories.crop_image_repository import CropImageRepository
from app.repositories.diagnosis_repository import DiagnosisRepository
from app.schemas.diagnosis import DiagnosisRequest
from app.services.exceptions import (
    DiagnosisPersistenceError,
    FarmNotFoundError,
    FarmPersistenceError,
    ImageFileNotFoundError,
    ImageNotFoundError,
)
from app.services.farm_service import FarmService
from app.services.vision_service import VisionService


CONFIDENCE_PRECISION = Decimal("0.0001")


class DiagnosisService:
    def __init__(self, db: Session):
        self.db = db
        self.farm_service = FarmService(db)
        self.crop_image_repository = CropImageRepository(db)
        self.diagnosis_repository = DiagnosisRepository(db)
        self.vision_service = VisionService()

    def diagnose_farm_image(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        diagnosis_in: DiagnosisRequest,
    ) -> Diagnosis:
        self._ensure_farm_owner(user_id, farm_id)
        crop_image = self._resolve_crop_image(farm_id, diagnosis_in.image_id)
        image_bytes = self._read_image_file(crop_image)

        vision_result = self.vision_service.diagnose_image(
            image_bytes=image_bytes,
            content_type=crop_image.content_type,
            image_file_path=crop_image.file_path,
        )
        payload = vision_result.payload

        diagnosis = Diagnosis(
            farm_id=farm_id,
            crop_image_id=crop_image.id,
            user_id=user_id,
            disease_name=payload.disease_name,
            confidence_score=Decimal(str(payload.confidence_score)).quantize(
                CONFIDENCE_PRECISION,
            ),
            severity=payload.severity,
            possible_causes=payload.possible_causes,
            organic_treatment=payload.organic_treatment,
            chemical_treatment=payload.chemical_treatment,
            prevention_steps=payload.prevention_steps,
            escalate_to_human=payload.escalate_to_human,
            raw_vision_output=vision_result.raw_output,
        )
        self.diagnosis_repository.add(diagnosis)

        try:
            self.db.commit()
            self.db.refresh(diagnosis)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise DiagnosisPersistenceError from exc

        return diagnosis

    def _ensure_farm_owner(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> None:
        try:
            self.farm_service.get_farm(user_id, farm_id)
        except FarmNotFoundError:
            raise
        except FarmPersistenceError as exc:
            raise DiagnosisPersistenceError from exc

    def _resolve_crop_image(
        self,
        farm_id: uuid.UUID,
        image_id: uuid.UUID | None,
    ) -> CropImage:
        try:
            if image_id is not None:
                crop_image = self.crop_image_repository.get_by_id_for_farm(
                    image_id,
                    farm_id,
                )
            else:
                crop_image = self.crop_image_repository.get_latest_by_farm(farm_id)
        except SQLAlchemyError as exc:
            raise DiagnosisPersistenceError from exc

        if crop_image is None:
            raise ImageNotFoundError
        return crop_image

    def _read_image_file(self, crop_image: CropImage) -> bytes:
        image_path = self._resolve_image_path(crop_image.file_path)
        if not image_path.is_file():
            raise ImageFileNotFoundError

        try:
            return image_path.read_bytes()
        except OSError as exc:
            raise ImageFileNotFoundError from exc

    def _resolve_image_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self._backend_root() / path

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]
