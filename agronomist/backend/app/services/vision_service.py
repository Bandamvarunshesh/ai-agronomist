from __future__ import annotations

import json
import logging
import re
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
Use any supplied farm, weather, soil, advisory, market, timeline, diagnosis, and knowledge context only as supporting context. Do not invent live data beyond what is supplied.
Return ONLY one valid JSON object and do not wrap it in markdown.
The JSON object MUST contain exactly these top-level keys:
- disease_name: string
- confidence_score: number between 0 and 1
- severity: string
- possible_causes: array of strings
- organic_treatment: array of strings
- chemical_treatment: array of strings
- prevention_steps: array of strings
- escalate_to_human: boolean
Do not rename keys.
Do not nest the diagnosis inside another object.
Do not include any extra commentary before or after the JSON.
Do not include markdown.
Do not include explanation outside JSON.
Never recommend a pesticide brand name.
Use active ingredient or treatment category instead.
If information is uncertain, keep confidence_score below 0.6 and set escalate_to_human to true.
If the crop looks healthy, set disease_name to "Healthy crop condition" and still return every required field."""

MAX_LOG_RESPONSE_CHARS = 4000

FIELD_ALIASES = {
    "disease_name": (
        "disease_name",
        "disease",
        "diagnosis",
        "condition",
        "condition_name",
        "issue",
        "issue_name",
        "name",
        "predicted_disease",
        "predicted_condition",
        "crop_condition",
        "health_status",
        "assessment",
    ),
    "confidence_score": (
        "confidence_score",
        "confidence",
        "confidence_level",
        "score",
        "probability",
        "likelihood",
        "certainty",
    ),
    "severity": (
        "severity",
        "severity_level",
        "risk_level",
        "seriousness",
        "urgency",
    ),
    "possible_causes": (
        "possible_causes",
        "causes",
        "likely_causes",
        "cause",
        "possible_reasons",
        "reasons",
    ),
    "organic_treatment": (
        "organic_treatment",
        "organic_treatments",
        "organic_control",
        "organic_controls",
        "organic_remedies",
        "natural_treatment",
        "natural_treatments",
        "natural_control",
        "natural_controls",
    ),
    "chemical_treatment": (
        "chemical_treatment",
        "chemical_treatments",
        "chemical_control",
        "chemical_controls",
        "chemical_remedies",
        "conventional_treatment",
        "conventional_treatments",
        "recommended_treatment",
        "recommended_treatments",
        "treatment",
        "treatments",
    ),
    "prevention_steps": (
        "prevention_steps",
        "prevention",
        "preventive_steps",
        "preventive_measures",
        "prevention_measures",
        "precautions",
    ),
    "escalate_to_human": (
        "escalate_to_human",
        "escalate",
        "human_review_required",
        "consult_expert",
        "expert_review_needed",
        "refer_to_expert",
    ),
}

SEVERITY_ALIASES = {
    "very low": "low",
    "low": "low",
    "mild": "low",
    "minor": "low",
    "none": "low",
    "healthy": "low",
    "moderate": "moderate",
    "medium": "moderate",
    "mid": "moderate",
    "high": "high",
    "severe": "high",
    "major": "high",
    "critical": "critical",
    "urgent": "critical",
    "unknown": "unknown",
    "uncertain": "unknown",
}

NESTED_OBJECT_ALIASES = (
    "diagnosis",
    "result",
    "analysis",
    "response",
    "output",
    "assessment",
)


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
        context_text: str | None = None,
    ) -> VisionDiagnosisResult:
        self._validate_configuration()

        try:
            client = genai.Client(
                api_key=settings.gemini_api_key,
                http_options=types.HttpOptions(
                    timeout=settings.gemini_request_timeout_seconds * 1000,
                ),
            )
            contents: list[Any] = [DIAGNOSIS_PROMPT]
            if context_text and context_text.strip():
                contents.append(f"Supporting context:\n{context_text.strip()}")
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type=content_type))

            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
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
            "context_text_used": context_text,
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
            "Gemini response text before JSON parsing: model=%s image_file_path=%s image_mime_type=%s response_text=%s response_length=%s",
            settings.gemini_model,
            image_file_path,
            content_type,
            self._safe_log_value(response_text),
            len(response_text),
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
            extracted_json = self._extract_json_object_text(response_text)
            if extracted_json is not None:
                try:
                    parsed_json = json.loads(extracted_json)
                except json.JSONDecodeError:
                    parsed_json = None
                else:
                    if isinstance(parsed_json, dict):
                        return parsed_json
                    if (
                        isinstance(parsed_json, list)
                        and parsed_json
                        and isinstance(parsed_json[0], dict)
                    ):
                        return parsed_json[0]

            logger.exception(
                "Gemini JSON parsing failed: model=%s image_file_path=%s image_mime_type=%s error=%s response_text=%s",
                settings.gemini_model,
                image_file_path,
                content_type,
                str(exc),
                self._safe_log_value(response_text),
            )
            raise VisionResponseParseError("Gemini returned invalid JSON") from exc

        if isinstance(parsed_json, list) and parsed_json and isinstance(parsed_json[0], dict):
            return parsed_json[0]
        if not isinstance(parsed_json, dict):
            logger.error(
                "Gemini JSON response was not an object: model=%s image_file_path=%s image_mime_type=%s response_text=%s",
                settings.gemini_model,
                image_file_path,
                content_type,
                self._safe_log_value(response_text),
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
        normalized_json, missing_fields = self._normalize_payload(parsed_json)
        try:
            payload = VisionDiagnosisPayload.model_validate(normalized_json)
        except ValidationError as exc:
            logger.exception(
                "Gemini JSON validation failed: model=%s image_file_path=%s image_mime_type=%s error=%s parsed_json=%s",
                settings.gemini_model,
                image_file_path,
                content_type,
                str(exc),
                self._safe_log_value(json.dumps(parsed_json, ensure_ascii=True)),
            )
            raise VisionResponseParseError(
                "Gemini JSON response is missing required diagnosis fields",
            ) from exc

        if missing_fields:
            payload = payload.model_copy(update={"escalate_to_human": True})
            logger.warning(
                "Gemini diagnosis response required safe defaults: model=%s image_file_path=%s image_mime_type=%s missing_fields=%s normalized_json=%s",
                settings.gemini_model,
                image_file_path,
                content_type,
                ",".join(missing_fields),
                self._safe_log_value(json.dumps(payload.model_dump(), ensure_ascii=True)),
            )
        return payload

    def _normalize_payload(
        self,
        parsed_json: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        source = self._flatten_candidate_payload(parsed_json)
        missing_fields: list[str] = []

        disease_name = self._normalize_text(
            self._find_value(source, "disease_name"),
        )
        if not disease_name:
            disease_name = "Uncertain crop condition"
            missing_fields.append("disease_name")

        confidence_score = self._normalize_confidence(
            self._find_value(source, "confidence_score"),
        )
        if confidence_score is None:
            confidence_score = 0.0
            missing_fields.append("confidence_score")

        severity = self._normalize_severity(self._find_value(source, "severity"))
        if not severity:
            severity = "unknown"
            missing_fields.append("severity")

        possible_causes = self._normalize_string_list(
            self._find_value(source, "possible_causes"),
        )
        if self._find_value(source, "possible_causes") is None:
            missing_fields.append("possible_causes")

        organic_treatment = self._normalize_string_list(
            self._find_value(source, "organic_treatment"),
        )
        if self._find_value(source, "organic_treatment") is None:
            missing_fields.append("organic_treatment")

        chemical_treatment = self._normalize_string_list(
            self._find_value(source, "chemical_treatment"),
        )
        if self._find_value(source, "chemical_treatment") is None:
            missing_fields.append("chemical_treatment")

        prevention_steps = self._normalize_string_list(
            self._find_value(source, "prevention_steps"),
        )
        if self._find_value(source, "prevention_steps") is None:
            missing_fields.append("prevention_steps")

        escalate_to_human = self._normalize_bool(
            self._find_value(source, "escalate_to_human"),
        )
        if escalate_to_human is None:
            escalate_to_human = True
            missing_fields.append("escalate_to_human")

        if missing_fields:
            escalate_to_human = True

        return (
            {
                "disease_name": disease_name,
                "confidence_score": confidence_score,
                "severity": severity,
                "possible_causes": possible_causes,
                "organic_treatment": organic_treatment,
                "chemical_treatment": chemical_treatment,
                "prevention_steps": prevention_steps,
                "escalate_to_human": escalate_to_human,
            },
            missing_fields,
        )

    def _flatten_candidate_payload(self, parsed_json: dict[str, Any]) -> dict[str, Any]:
        flattened = dict(parsed_json)
        for key in NESTED_OBJECT_ALIASES:
            nested = parsed_json.get(key)
            if isinstance(nested, dict):
                for nested_key, nested_value in nested.items():
                    flattened.setdefault(nested_key, nested_value)
        return flattened

    def _find_value(self, source: dict[str, Any], field_name: str) -> Any:
        aliases = FIELD_ALIASES[field_name]
        normalized_source = {
            self._normalize_key(key): value for key, value in source.items()
        }
        for alias in aliases:
            normalized_alias = self._normalize_key(alias)
            if normalized_alias in normalized_source:
                return normalized_source[normalized_alias]
        return None

    def _normalize_key(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.strip().lower())

    def _normalize_text(self, value: Any) -> str | None:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return None

    def _normalize_confidence(self, value: Any) -> float | None:
        numeric_value: float | None = None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            numeric_value = float(value)
        elif isinstance(value, str):
            cleaned = value.strip().rstrip("%")
            try:
                numeric_value = float(cleaned)
            except ValueError:
                return None

        if numeric_value is None:
            return None
        if 0 <= numeric_value <= 1:
            return numeric_value
        if 1 < numeric_value <= 100:
            return numeric_value / 100
        return None

    def _normalize_severity(self, value: Any) -> str | None:
        text = self._normalize_text(value)
        if not text:
            return None
        normalized = SEVERITY_ALIASES.get(text.lower())
        if normalized is not None:
            return normalized
        return text.lower()

    def _normalize_string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = re.split(r"(?:\r?\n|;|,|\|)", value)
            return [cleaned for item in parts if (cleaned := " ".join(item.split()))]
        if isinstance(value, list):
            cleaned_items: list[str] = []
            for item in value:
                if isinstance(item, str):
                    cleaned = " ".join(item.split())
                    if cleaned:
                        cleaned_items.append(cleaned)
                elif isinstance(item, dict):
                    text = self._normalize_text(
                        item.get("text") or item.get("name") or item.get("title"),
                    )
                    if text:
                        cleaned_items.append(text)
            return cleaned_items
        return []

    def _normalize_bool(self, value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "yes", "y", "1"}:
                return True
            if normalized in {"false", "no", "n", "0"}:
                return False
        return None

    def _extract_json_object_text(self, response_text: str) -> str | None:
        stripped = response_text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
            stripped = re.sub(r"\s*```$", "", stripped)

        start = stripped.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(stripped)):
            character = stripped[index]
            if in_string:
                if escape:
                    escape = False
                elif character == "\\":
                    escape = True
                elif character == '"':
                    in_string = False
                continue

            if character == '"':
                in_string = True
            elif character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    return stripped[start : index + 1]
        return None

    def _safe_log_value(self, value: str) -> str:
        if len(value) <= MAX_LOG_RESPONSE_CHARS:
            return value
        return f"{value[:MAX_LOG_RESPONSE_CHARS]}...[truncated]"
