from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StageWindowRead(BaseModel):
    name: str
    stage_order: Optional[int] = None
    start_day: Optional[int] = None
    end_day: Optional[int] = None


class StageDiagnosisContextRead(BaseModel):
    id: uuid.UUID
    disease_name: str
    severity: str
    confidence_score: float
    escalate_to_human: bool
    created_at: datetime


class StageWeatherContextRead(BaseModel):
    source: str
    summary: str
    unavailable_reason: Optional[str] = None


class StageAdvisoryRead(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    crop: str
    days_since_sowing: Optional[int]
    current_stage: StageWindowRead
    next_stage: Optional[StageWindowRead]
    important_actions: list[str]
    risks: list[str]
    ai_recommendations: list[str]
    latest_diagnosis: Optional[StageDiagnosisContextRead]
    weather_context: StageWeatherContextRead
    generated_at: datetime
