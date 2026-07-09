from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.crop import CropImage, Diagnosis
from app.models.farm import Farm
from app.repositories.crop_image_repository import CropImageRepository
from app.repositories.diagnosis_repository import DiagnosisRepository
from app.schemas.diagnosis import DiagnosisRequest
from app.services.exceptions import (
    DiagnosisPersistenceError,
    EscalationContactPersistenceError,
    EscalationPersistenceError,
    FarmNotFoundError,
    FarmPersistenceError,
    ImageFileNotFoundError,
    ImageNotFoundError,
    NotificationPersistenceError,
)
from app.services.escalation_service import EscalationService
from app.services.farm_intelligence_service import FarmIntelligenceService
from app.services.farm_service import FarmService
from app.services.knowledge_service import KnowledgeService
from app.services.notification_generation_service import NotificationGenerationService
from app.services.stage_advisory_service import StageAdvisoryService
from app.services.storage_service import StorageService
from app.services.timeline_service import TimelineService
from app.services.vision_service import VisionService


CONFIDENCE_PRECISION = Decimal("0.0001")


class DiagnosisService:
    def __init__(self, db: Session):
        self.db = db
        self.farm_service = FarmService(db)
        self.crop_image_repository = CropImageRepository(db)
        self.diagnosis_repository = DiagnosisRepository(db)
        self.escalation_service = EscalationService(db)
        self.farm_intelligence_service = FarmIntelligenceService(db)
        self.knowledge_service = KnowledgeService(db)
        self.notification_generation_service = NotificationGenerationService(db)
        self.stage_advisory_service = StageAdvisoryService(db)
        self.timeline_service = TimelineService(db)
        self.storage_service = StorageService()
        self.vision_service = VisionService()

    def diagnose_farm_image(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        diagnosis_in: DiagnosisRequest,
    ) -> Diagnosis:
        farm = self._ensure_farm_owner(user_id, farm_id)
        crop_image = self._resolve_crop_image(farm_id, diagnosis_in.image_id)
        image_bytes = self._read_image_file(crop_image)
        context_text = self._build_diagnosis_context(
            user_id=user_id,
            farm=farm,
        )

        vision_result = self.vision_service.diagnose_image(
            image_bytes=image_bytes,
            content_type=crop_image.content_type,
            image_file_path=crop_image.file_path,
            context_text=context_text,
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
            self.db.flush()
            self.timeline_service.add_event(
                farm_id=farm_id,
                user_id=user_id,
                event_type="diagnosis",
                title=f"Diagnosis: {diagnosis.disease_name}",
                description=(
                    f"{diagnosis.severity} severity with "
                    f"{diagnosis.confidence_score} confidence"
                ),
                source="diagnosis",
                payload={
                    "diagnosis_id": str(diagnosis.id),
                    "crop_image_id": str(crop_image.id),
                    "disease_name": diagnosis.disease_name,
                    "severity": diagnosis.severity,
                    "confidence_score": str(diagnosis.confidence_score),
                    "escalate_to_human": diagnosis.escalate_to_human,
                },
            )
            self.notification_generation_service.add_for_high_risk_diagnosis(
                user_id=user_id,
                farm=farm,
                diagnosis=diagnosis,
            )
            self.escalation_service.create_for_diagnosis_if_needed(
                user_id=user_id,
                farm=farm,
                diagnosis=diagnosis,
            )
            self.db.commit()
            self.db.refresh(diagnosis)
        except (
            SQLAlchemyError,
            NotificationPersistenceError,
            EscalationContactPersistenceError,
            EscalationPersistenceError,
        ) as exc:
            self.db.rollback()
            raise DiagnosisPersistenceError from exc

        return diagnosis

    def _ensure_farm_owner(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> Farm:
        try:
            return self.farm_service.get_farm(user_id, farm_id)
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
        try:
            return self.storage_service.read_bytes(crop_image.file_path)
        except OSError as exc:
            raise ImageFileNotFoundError from exc

    def _build_diagnosis_context(
        self,
        *,
        user_id: uuid.UUID,
        farm: Farm,
    ) -> str | None:
        lines: list[str] = []
        try:
            intelligence_snapshot, intelligence_text = self.farm_intelligence_service.build_ai_context(
                user_id=user_id,
                farm_id=farm.id,
            )
            del intelligence_snapshot
            if intelligence_text:
                lines.append(intelligence_text)
        except Exception:
            lines.append("External agricultural intelligence: unavailable.")

        try:
            stage_advisory = self.stage_advisory_service.get_stage_advisory(
                user_id=user_id,
                farm_id=farm.id,
                log_timeline=False,
            )
            lines.append(
                "Crop stage advisory:\n"
                f"- Current stage: {stage_advisory.current_stage.name}\n"
                f"- Risks: {', '.join(stage_advisory.risks[:5]) if stage_advisory.risks else 'none'}\n"
                f"- Important actions: {', '.join(stage_advisory.important_actions[:5]) if stage_advisory.important_actions else 'none'}"
            )
        except Exception:
            lines.append("Crop stage advisory: unavailable.")

        try:
            previous_diagnoses = self.diagnosis_repository.list_by_farm(
                farm.id,
                skip=0,
                limit=5,
            )
            if previous_diagnoses:
                lines.append(
                    "Previous diagnoses:\n"
                    + "\n".join(
                        f"- {item.created_at.date().isoformat()}: {item.disease_name}; severity {item.severity}; confidence {item.confidence_score}"
                        for item in previous_diagnoses
                    )
                )
        except Exception:
            pass

        try:
            timeline_events = self.timeline_service.list_events(
                user_id=user_id,
                farm_id=farm.id,
                limit=8,
            )
            if timeline_events:
                lines.append(
                    "Recent farm timeline:\n"
                    + "\n".join(
                        f"- {event.event_date.date().isoformat()}: {event.title}"
                        for event in timeline_events[:5]
                    )
                )
        except Exception:
            pass

        try:
            query = " ".join(part for part in [farm.crop, farm.district, farm.state, farm.soil_type or ""] if part)
            rag_context, _citations = self.knowledge_service.build_rag_context(query=query, limit=4)
            if rag_context:
                lines.append(rag_context)
        except Exception:
            pass

        context_text = "\n\n".join(line for line in lines if line.strip())
        return context_text or None
