from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.diagnosis import VisionDiagnosisPayload
from app.services.exceptions import (
    VisionConfigurationError,
    VisionProviderError,
    VisionResponseParseError,
)


logger = logging.getLogger(__name__)

DIAGNOSIS_PROMPT = """You are an expert agricultural plant disease diagnostician.
Analyze this crop image.
Identify whether the image shows disease, pest damage, nutrient deficiency, or healthy crop condition.
Return ONLY valid JSON with these keys:
disease_name, confidence_score, severity, possible_causes, organic_treatment, chemical_treatment, prevention_steps, escalate_to_human.
Do not include markdown.
Do not include explanation outside JSON.
Never recommend a pesticide brand name.
Use active ingredient or treatment category instead.
If unsure, set confidence_score below 0.6 and escalate_to_human true."""


@dataclass(frozen=True)
class VisionDiagnosisResult:
    payload: VisionDiagnosisPayload
    raw_output: dict[str, Any]


class VisionService:
    def diagnose_image(
        self,
        *,
        image_bytes: bytes,
        content_type: str,
        image_file_path: str,
    ) -> VisionDiagnosisResult:
        self._validate_configuration()

        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=[
                    DIAGNOSIS_PROMPT,
                    types.Part.from_bytes(data=image_bytes, mime_type=content_type),
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            response_text = self._extract_response_text(response)
        except VisionResponseParseError as exc:
            logger.exception(
                "Gemini Vision response handling failed: model=%s image_file_path=%s image_mime_type=%s error=%s",
                settings.gemini_model,
                image_file_path,
                content_type,
                str(exc),
            )
            raise
        except Exception as exc:
            logger.exception(
                "Gemini Vision request failed: model=%s image_file_path=%s image_mime_type=%s error=%s",
                settings.gemini_model,
                image_file_path,
                content_type,
                str(exc),
            )
            raise VisionProviderError("Gemini Vision request failed") from exc

        self._log_response_text(
            response_text=response_text,
            image_file_path=image_file_path,
            content_type=content_type,
        )
        parsed_json = self._parse_json(
            response_text,
            image_file_path=image_file_path,
            content_type=content_type,
        )
        payload = self._validate_payload(
            parsed_json,
            image_file_path=image_file_path,
            content_type=content_type,
        )
        if payload.confidence_score < 0.6:
            payload = payload.model_copy(update={"escalate_to_human": True})

        raw_output = {
            "provider": settings.vision_provider,
            "model": settings.gemini_model,
            "response_text": response_text,
            "parsed_json": parsed_json,
            "normalized_json": payload.model_dump(),
        }
        return VisionDiagnosisResult(payload=payload, raw_output=raw_output)

    def _validate_configuration(self) -> None:
        if settings.vision_provider.lower() != "gemini":
            raise VisionConfigurationError("VISION_PROVIDER must be set to 'gemini'")
        if not settings.gemini_api_key.strip():
            raise VisionConfigurationError("GEMINI_API_KEY is not configured")

    def _extract_response_text(self, response: Any) -> str:
        response_text = getattr(response, "output_text", None) or getattr(
            response,
            "text",
            "",
        )
        if not isinstance(response_text, str) or not response_text.strip():
            raise VisionResponseParseError("Gemini returned an empty response")
        return response_text.strip()

    def _log_response_text(
        self,
        *,
        response_text: str,
        image_file_path: str,
        content_type: str,
    ) -> None:
        logger.info(
            "Gemini response text before JSON parsing: model=%s image_file_path=%s image_mime_type=%s response_text=%s",
            settings.gemini_model,
            image_file_path,
            content_type,
            response_text,
        )

    def _parse_json(
        self,
        response_text: str,
        *,
        image_file_path: str,
        content_type: str,
    ) -> dict[str, Any]:
        try:
            parsed_json = json.loads(response_text)
        except json.JSONDecodeError as exc:
            logger.exception(
                "Gemini JSON parsing failed: model=%s image_file_path=%s image_mime_type=%s error=%s response_text=%s",
                settings.gemini_model,
                image_file_path,
                content_type,
                str(exc),
                response_text,
            )
            raise VisionResponseParseError("Gemini returned invalid JSON") from exc

        if not isinstance(parsed_json, dict):
            logger.error(
                "Gemini JSON response was not an object: model=%s image_file_path=%s image_mime_type=%s response_text=%s",
                settings.gemini_model,
                image_file_path,
                content_type,
                response_text,
            )
            raise VisionResponseParseError("Gemini JSON response must be an object")
        return parsed_json

    def _validate_payload(
        self,
        parsed_json: dict[str, Any],
        *,
        image_file_path: str,
        content_type: str,
    ) -> VisionDiagnosisPayload:
        try:
            return VisionDiagnosisPayload.model_validate(parsed_json)
        except ValidationError as exc:
            logger.exception(
                "Gemini JSON validation failed: model=%s image_file_path=%s image_mime_type=%s error=%s parsed_json=%s",
                settings.gemini_model,
                image_file_path,
                content_type,
                str(exc),
                parsed_json,
            )
            raise VisionResponseParseError(
                "Gemini JSON response is missing required diagnosis fields",
            ) from exc
