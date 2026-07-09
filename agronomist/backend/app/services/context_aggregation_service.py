from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage
from app.models.crop import Diagnosis
from app.models.farm import Farm
from app.models.timeline import TimelineEvent
from app.repositories.chat_repository import ChatRepository
from app.schemas.stage_advisory import StageAdvisoryRead
from app.schemas.weather import FarmWeatherRead
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    RecommendationContextError,
    StageAdvisoryPersistenceError,
    TimelinePersistenceError,
    WeatherLocationNotFoundError,
    WeatherProviderError,
    WeatherResponseParseError,
)
from app.services.farm_intelligence_service import FarmIntelligenceService
from app.services.farm_service import FarmService
from app.services.knowledge_service import KnowledgeService
from app.services.stage_advisory_service import StageAdvisoryService
from app.services.timeline_service import TimelineService


@dataclass(frozen=True)
class RecommendationContext:
    farm: Farm
    latest_diagnosis: Diagnosis | None
    weather: FarmWeatherRead | None
    weather_unavailable_reason: str | None
    farm_intelligence: dict[str, Any] | None
    stage_advisory: StageAdvisoryRead
    timeline_events: Sequence[TimelineEvent]
    chat_messages: Sequence[ChatMessage]
    knowledge_context: str
    knowledge_citations: list[dict[str, Any]]
    generated_at: datetime

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "farm_profile": self._farm_snapshot(),
            "latest_diagnosis": self._diagnosis_snapshot(self.latest_diagnosis),
            "weather": self._weather_snapshot(),
            "farm_intelligence": self.farm_intelligence,
            "crop_stage_advisory": self.stage_advisory.model_dump(mode="json"),
            "timeline": [
                self._timeline_event_snapshot(event) for event in self.timeline_events
            ],
            "chat_context": [
                self._chat_message_snapshot(message) for message in self.chat_messages
            ],
            "rag_context": {
                "available": bool(self.knowledge_context),
                "context": self.knowledge_context,
                "citations": self.knowledge_citations,
            },
        }

    def _farm_snapshot(self) -> dict[str, Any]:
        return {
            "id": str(self.farm.id),
            "farm_name": self.farm.farm_name,
            "crop": self.farm.crop,
            "location": self.farm.location,
            "village": self.farm.village,
            "district": self.farm.district,
            "state": self.farm.state,
            "soil_type": self.farm.soil_type,
            "land_size_acres": self._decimal_to_float(self.farm.land_size_acres),
            "irrigation_type": self.farm.irrigation_type,
            "sowing_date": (
                self.farm.sowing_date.isoformat() if self.farm.sowing_date else None
            ),
        }

    def _weather_snapshot(self) -> dict[str, Any]:
        if self.weather is None:
            return {
                "available": False,
                "source": "Open-Meteo",
                "unavailable_reason": self.weather_unavailable_reason,
            }

        return {
            "available": True,
            "data": self.weather.model_dump(mode="json"),
        }

    def _diagnosis_snapshot(self, diagnosis: Diagnosis | None) -> dict[str, Any] | None:
        if diagnosis is None:
            return None

        return {
            "id": str(diagnosis.id),
            "disease_name": diagnosis.disease_name,
            "confidence_score": self._decimal_to_float(diagnosis.confidence_score),
            "severity": diagnosis.severity,
            "possible_causes": diagnosis.possible_causes,
            "organic_treatment": diagnosis.organic_treatment,
            "chemical_treatment": diagnosis.chemical_treatment,
            "prevention_steps": diagnosis.prevention_steps,
            "escalate_to_human": diagnosis.escalate_to_human,
            "created_at": diagnosis.created_at.isoformat(),
        }

    def _timeline_event_snapshot(self, event: TimelineEvent) -> dict[str, Any]:
        return {
            "id": str(event.id),
            "event_type": event.event_type,
            "title": event.title,
            "description": event.description,
            "event_date": event.event_date.isoformat(),
            "source": event.source,
            "payload": event.payload,
            "created_at": event.created_at.isoformat(),
        }

    def _chat_message_snapshot(self, message: ChatMessage) -> dict[str, Any]:
        return {
            "id": str(message.id),
            "role": message.role,
            "content": self._truncate_text(message.content, max_length=900),
            "sent_at": message.sent_at.isoformat(),
        }

    def _decimal_to_float(self, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    def _truncate_text(self, value: str, *, max_length: int) -> str:
        text = " ".join(value.split())
        if len(text) <= max_length:
            return text
        return f"{text[: max_length - 3].rstrip()}..."


class ContextAggregationService:
    def __init__(self, db: Session):
        self.db = db
        self.farm_service = FarmService(db)
        self.chat_repository = ChatRepository(db)
        self.farm_intelligence_service = FarmIntelligenceService(db)
        self.knowledge_service = KnowledgeService(db)
        self.stage_advisory_service = StageAdvisoryService(db)
        self.timeline_service = TimelineService(db)

    def build_recommendation_context(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> RecommendationContext:
        farm = self._get_farm(user_id=user_id, farm_id=farm_id)
        latest_diagnosis = self._get_latest_diagnosis(
            user_id=user_id,
            farm_id=farm_id,
        )
        farm_intelligence = self._get_farm_intelligence(
            user_id=user_id,
            farm_id=farm_id,
        )
        weather, weather_unavailable_reason = self._get_weather_from_intelligence(
            farm_intelligence=farm_intelligence,
        )
        if weather is None:
            weather, weather_unavailable_reason = self._get_weather(
                user_id=user_id,
                farm_id=farm_id,
            )
        stage_advisory = self._get_stage_advisory(
            user_id=user_id,
            farm_id=farm_id,
        )
        timeline_events = self._get_timeline_events(
            user_id=user_id,
            farm_id=farm_id,
        )
        chat_messages = self._get_chat_messages(user_id=user_id, farm_id=farm_id)
        knowledge_context, knowledge_citations = self._get_knowledge_context(
            farm=farm,
            stage_advisory=stage_advisory,
            latest_diagnosis=latest_diagnosis,
        )

        return RecommendationContext(
            farm=farm,
            latest_diagnosis=latest_diagnosis,
            weather=weather,
            weather_unavailable_reason=weather_unavailable_reason,
            farm_intelligence=farm_intelligence,
            stage_advisory=stage_advisory,
            timeline_events=timeline_events,
            chat_messages=chat_messages,
            knowledge_context=knowledge_context,
            knowledge_citations=knowledge_citations,
            generated_at=datetime.now(timezone.utc),
        )

    def _get_farm(self, *, user_id: uuid.UUID, farm_id: uuid.UUID) -> Farm:
        try:
            return self.farm_service.get_farm(user_id, farm_id)
        except FarmNotFoundError:
            raise
        except FarmPersistenceError:
            raise
        except SQLAlchemyError as exc:
            raise FarmPersistenceError from exc

    def _get_latest_diagnosis(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> Diagnosis | None:
        try:
            diagnoses = self.chat_repository.list_recent_diagnoses_for_user(
                user_id,
                farm_id=farm_id,
                limit=1,
            )
        except SQLAlchemyError as exc:
            raise RecommendationContextError(
                "Unable to read latest diagnosis context",
            ) from exc

        return diagnoses[0] if diagnoses else None

    def _get_weather(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> tuple[FarmWeatherRead | None, str | None]:
        try:
            weather = self.farm_intelligence_service.get_farm_weather_response(
                user_id=user_id,
                farm_id=farm_id,
            )
        except (
            WeatherLocationNotFoundError,
            WeatherProviderError,
            WeatherResponseParseError,
        ) as exc:
            return None, str(exc)

        return weather, None

    def _get_farm_intelligence(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        try:
            intelligence = self.farm_intelligence_service.get_farm_intelligence(
                user_id=user_id,
                farm_id=farm_id,
            )
        except Exception:
            return None
        return intelligence.model_dump(mode="json")

    def _get_weather_from_intelligence(
        self,
        *,
        farm_intelligence: dict[str, Any] | None,
    ) -> tuple[FarmWeatherRead | None, str | None]:
        if not farm_intelligence:
            return None, None
        weather = farm_intelligence.get("weather")
        resolved_location = farm_intelligence.get("resolved_location")
        forecast = farm_intelligence.get("forecast")
        if not isinstance(weather, dict) or not isinstance(resolved_location, dict) or not isinstance(forecast, list):
            unavailable = farm_intelligence.get("unavailable") or {}
            reason = unavailable.get("weather") if isinstance(unavailable, dict) else None
            return None, reason
        try:
            return (
                FarmWeatherRead(
                    farm_id=farm_intelligence["farm_id"],
                    farm_name=farm_intelligence["farm_name"],
                    crop=farm_intelligence["crop"],
                    resolved_location=resolved_location,
                    current=weather,
                    forecast=forecast,
                    advice={
                        "irrigation": [],
                        "rainfall": [],
                        "spraying": [],
                        "heat": [],
                        "wind": [],
                        "humidity": [],
                    },
                    source="farm-intelligence",
                    fetched_at=farm_intelligence["generated_at"],
                ),
                None,
            )
        except Exception:
            return None, "Unable to normalize weather from farm intelligence"

    def _get_stage_advisory(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> StageAdvisoryRead:
        try:
            return self.stage_advisory_service.get_stage_advisory(
                user_id=user_id,
                farm_id=farm_id,
                log_timeline=False,
            )
        except StageAdvisoryPersistenceError as exc:
            raise RecommendationContextError(
                "Unable to build crop stage advisory context",
            ) from exc

    def _get_timeline_events(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> Sequence[TimelineEvent]:
        try:
            return self.timeline_service.list_events(
                user_id=user_id,
                farm_id=farm_id,
                limit=25,
            )
        except TimelinePersistenceError as exc:
            raise RecommendationContextError(
                "Unable to read farm timeline context",
            ) from exc

    def _get_chat_messages(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> Sequence[ChatMessage]:
        try:
            return self.chat_repository.list_recent_messages_for_farm(
                user_id=user_id,
                farm_id=farm_id,
                limit=12,
            )
        except SQLAlchemyError as exc:
            raise RecommendationContextError(
                "Unable to read recent chat context",
            ) from exc

    def _get_knowledge_context(
        self,
        *,
        farm: Farm,
        stage_advisory: StageAdvisoryRead,
        latest_diagnosis: Diagnosis | None,
    ) -> tuple[str, list[dict[str, Any]]]:
        query_parts = [
            farm.crop,
            farm.soil_type or "",
            farm.irrigation_type or "",
            farm.district,
            farm.state,
            stage_advisory.current_stage.name,
            " ".join(stage_advisory.risks[:3]),
        ]
        if latest_diagnosis is not None:
            query_parts.append(latest_diagnosis.disease_name)
        query = " ".join(part for part in query_parts if part)
        return self.knowledge_service.build_rag_context(query=query, limit=6)
