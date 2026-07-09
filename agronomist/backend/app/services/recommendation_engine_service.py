from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.recommendation import FarmRecommendation
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.recommendation import RecommendationGenerationPayload
from app.services.context_aggregation_service import ContextAggregationService
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    NotificationPersistenceError,
    RecommendationConfigurationError,
    RecommendationPersistenceError,
    RecommendationProviderError,
    RecommendationResponseParseError,
)
from app.services.farm_service import FarmService
from app.services.notification_generation_service import NotificationGenerationService


logger = logging.getLogger(__name__)


RECOMMENDATION_SYSTEM_INSTRUCTION = """You are an AI recommendation engine for farm decision support.
Use only the supplied farm context, weather context, external intelligence, crop-stage advisory, diagnosis history, timeline, chat context, and general agronomic safety principles.

Required behavior:
- Return only valid JSON. Do not include markdown, comments, citations, or prose outside JSON.
- Make practical recommendations across crops, soil, irrigation, fertilizer, pests, diseases, seeds, weather decisions, harvest, storage, livestock basics, equipment, organic farming, government schemes, and market preparation when relevant.
- Work even when RAG/document context is unavailable.
- Do not recommend pesticide, herbicide, fungicide, fertilizer, veterinary drug, or equipment brand names.
- Do not provide precise chemical, pesticide, veterinary medicine, fumigant, fertilizer dosage, mixing ratio, withdrawal period, or spray interval unless the supplied context explicitly verifies it.
- For severe crop loss, spreading disease, animal illness, poisoning, unknown chemical exposure, dangerous equipment, or financial/legal scheme decisions, recommend a local agronomist, veterinarian, extension officer, or relevant official.
- Prefer monitoring, cultural practices, irrigation timing, drainage, sanitation, soil testing, label/extension guidance, and safer next steps.
- Reflect uncertainty in the confidence score and explanations.
"""


RECOMMENDATION_JSON_CONTRACT = {
    "farm_health_score": "number from 0 to 100; 100 is excellent condition",
    "risk_level": "one of: low, moderate, high, critical",
    "prioritized_recommendations": [
        {
            "priority": "integer starting at 1; most urgent first",
            "category": "short category such as irrigation, pest, disease, nutrition, market, livestock, equipment",
            "title": "short action title",
            "recommendation": "specific practical action without unsafe dosage claims or brand names",
            "explanation": "why this action matters based on the supplied context",
            "risk_level": "one of: low, moderate, high, critical",
            "action_window": "when to act, such as today, next 48 hours, this week, before harvest",
        }
    ],
    "daily_action_plan": [
        {
            "day": "today, tomorrow, day 3, etc.",
            "actions": ["one or more safe, practical actions"],
            "explanation": "brief reason for the day's actions",
        }
    ],
    "weekly_summary": "brief summary of the next 7 days",
    "confidence_score": "number from 0 to 1",
}


class RecommendationEngineService:
    def __init__(self, db: Session):
        self.db = db
        self.farm_service = FarmService(db)
        self.context_service = ContextAggregationService(db)
        self.notification_generation_service = NotificationGenerationService(db)
        self.repository = RecommendationRepository(db)

    def list_recommendations(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[FarmRecommendation]:
        self._ensure_farm_owner(user_id=user_id, farm_id=farm_id)
        try:
            return self.repository.list_by_farm(farm_id, skip=skip, limit=limit)
        except SQLAlchemyError as exc:
            raise RecommendationPersistenceError from exc

    def generate_recommendation(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> FarmRecommendation:
        context = self.context_service.build_recommendation_context(
            user_id=user_id,
            farm_id=farm_id,
        )
        context_snapshot = context.to_snapshot()
        model_payload, raw_model_output = self._generate_model_payload(context_snapshot)
        prioritized_recommendations = sorted(
            model_payload.prioritized_recommendations,
            key=lambda item: item.priority,
        )

        recommendation = FarmRecommendation(
            farm_id=farm_id,
            user_id=user_id,
            farm_health_score=self._decimal_score(
                model_payload.farm_health_score,
                places="0.01",
            ),
            risk_level=model_payload.risk_level,
            prioritized_recommendations=[
                item.model_dump() for item in prioritized_recommendations
            ],
            daily_action_plan=[
                item.model_dump() for item in model_payload.daily_action_plan
            ],
            weekly_summary=model_payload.weekly_summary,
            confidence_score=self._decimal_score(
                model_payload.confidence_score,
                places="0.0001",
            ),
            context_snapshot=context_snapshot,
            raw_model_output=raw_model_output,
            generated_at=context.generated_at,
        )
        self.repository.add(recommendation)

        try:
            self.db.flush()
            self.notification_generation_service.add_for_recommendation(
                user_id=user_id,
                farm=context.farm,
                recommendation=recommendation,
            )
            self.db.commit()
            self.db.refresh(recommendation)
        except (SQLAlchemyError, NotificationPersistenceError) as exc:
            self.db.rollback()
            raise RecommendationPersistenceError from exc

        return recommendation

    def _ensure_farm_owner(self, *, user_id: uuid.UUID, farm_id: uuid.UUID) -> None:
        try:
            self.farm_service.get_farm(user_id, farm_id)
        except FarmNotFoundError:
            raise
        except FarmPersistenceError:
            raise
        except SQLAlchemyError as exc:
            raise FarmPersistenceError from exc

    def _generate_model_payload(
        self,
        context_snapshot: dict[str, Any],
    ) -> tuple[RecommendationGenerationPayload, dict[str, Any]]:
        self._validate_configuration()
        prompt = self._build_prompt(context_snapshot)

        try:
            client = genai.Client(
                api_key=settings.gemini_api_key,
                http_options=types.HttpOptions(
                    timeout=settings.gemini_request_timeout_seconds * 1000,
                ),
            )
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=prompt)],
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    system_instruction=RECOMMENDATION_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                ),
            )
            response_text = self._extract_response_text(response)
        except (RecommendationProviderError, RecommendationResponseParseError):
            raise
        except Exception as exc:
            logger.exception(
                "Gemini recommendation request failed: model=%s error=%s",
                settings.gemini_model,
                str(exc),
            )
            raise RecommendationProviderError(
                "Gemini recommendation request failed",
            ) from exc

        raw_payload = self._parse_json_payload(response_text)
        try:
            payload = RecommendationGenerationPayload.model_validate(raw_payload)
        except ValidationError as exc:
            raise RecommendationResponseParseError(
                "Gemini recommendation JSON did not match the expected schema",
            ) from exc

        return payload, raw_payload

    def _validate_configuration(self) -> None:
        if not settings.gemini_api_key.strip():
            raise RecommendationConfigurationError("GEMINI_API_KEY is not configured")

    def _build_prompt(self, context_snapshot: dict[str, Any]) -> str:
        context_json = json.dumps(
            context_snapshot,
            ensure_ascii=True,
            default=str,
            indent=2,
        )
        contract_json = json.dumps(
            RECOMMENDATION_JSON_CONTRACT,
            ensure_ascii=True,
            indent=2,
        )
        return "\n\n".join(
            [
                f"Current date: {date.today().isoformat()}",
                "Create a farm recommendation report from the supplied context.",
                "JSON contract to follow exactly:",
                contract_json,
                "Farm context:",
                context_json,
                "Return only one JSON object that follows the contract.",
            ]
        )

    def _extract_response_text(self, response: Any) -> str:
        response_text = getattr(response, "output_text", None) or getattr(
            response,
            "text",
            "",
        )
        if not isinstance(response_text, str) or not response_text.strip():
            raise RecommendationProviderError(
                "Gemini returned an empty recommendation response",
            )
        return response_text.strip()

    def _parse_json_payload(self, response_text: str) -> dict[str, Any]:
        json_text = self._strip_json_fence(response_text)
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise RecommendationResponseParseError(
                "Gemini recommendation response was not valid JSON",
            ) from exc

        if not isinstance(payload, dict):
            raise RecommendationResponseParseError(
                "Gemini recommendation response must be a JSON object",
            )
        return payload

    def _strip_json_fence(self, response_text: str) -> str:
        text = response_text.strip()
        fence_match = re.search(
            r"```(?:json)?\s*(.*?)```",
            text,
            flags=re.IGNORECASE | re.S,
        )
        if fence_match is not None:
            text = fence_match.group(1).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RecommendationResponseParseError(
                "Gemini recommendation response did not contain a JSON object",
            )
        return text[start : end + 1]

    def _decimal_score(self, value: float, *, places: str) -> Decimal:
        return Decimal(str(value)).quantize(Decimal(places))
