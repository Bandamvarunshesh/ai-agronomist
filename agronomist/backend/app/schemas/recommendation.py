from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


RISK_LEVEL_ALIASES = {
    "low": "low",
    "medium": "moderate",
    "moderate": "moderate",
    "high": "high",
    "critical": "critical",
    "severe": "critical",
}


class RecommendationItemRead(BaseModel):
    priority: int = Field(ge=1, le=20)
    category: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    recommendation: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    risk_level: str = Field(min_length=1, max_length=32)
    action_window: Optional[str] = Field(default=None, max_length=120)

    @field_validator("category", "title", "recommendation", "explanation")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("text cannot be blank")
        return cleaned

    @field_validator("risk_level")
    @classmethod
    def normalize_risk_level(cls, value: str) -> str:
        normalized = RISK_LEVEL_ALIASES.get(value.strip().lower())
        if normalized is None:
            raise ValueError("risk_level must be low, moderate, high, or critical")
        return normalized

    @field_validator("action_window")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class DailyActionPlanItemRead(BaseModel):
    day: str = Field(min_length=1, max_length=80)
    actions: list[str] = Field(min_length=1, max_length=10)
    explanation: Optional[str] = None

    @field_validator("day")
    @classmethod
    def strip_day(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("day cannot be blank")
        return cleaned

    @field_validator("actions")
    @classmethod
    def strip_actions(cls, values: list[str]) -> list[str]:
        cleaned_values = [" ".join(value.split()) for value in values]
        cleaned_values = [value for value in cleaned_values if value]
        if not cleaned_values:
            raise ValueError("actions cannot be empty")
        return cleaned_values

    @field_validator("explanation")
    @classmethod
    def strip_explanation(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class RecommendationGenerationPayload(BaseModel):
    farm_health_score: float = Field(ge=0, le=100)
    risk_level: str = Field(min_length=1, max_length=32)
    prioritized_recommendations: list[RecommendationItemRead] = Field(
        min_length=1,
        max_length=10,
    )
    daily_action_plan: list[DailyActionPlanItemRead] = Field(
        min_length=1,
        max_length=7,
    )
    weekly_summary: str = Field(min_length=1)
    confidence_score: float = Field(ge=0, le=1)

    @field_validator("risk_level")
    @classmethod
    def normalize_risk_level(cls, value: str) -> str:
        normalized = RISK_LEVEL_ALIASES.get(value.strip().lower())
        if normalized is None:
            raise ValueError("risk_level must be low, moderate, high, or critical")
        return normalized

    @field_validator("weekly_summary")
    @classmethod
    def strip_weekly_summary(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("weekly_summary cannot be blank")
        return cleaned


class FarmRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farm_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    farm_health_score: float
    risk_level: str
    prioritized_recommendations: list[RecommendationItemRead]
    daily_action_plan: list[DailyActionPlanItemRead]
    weekly_summary: str
    confidence_score: float
    generated_at: datetime
    created_at: datetime
    updated_at: datetime
