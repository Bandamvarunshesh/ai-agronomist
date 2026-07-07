from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiagnosisRequest(BaseModel):
    image_id: Optional[uuid.UUID] = None


class VisionDiagnosisPayload(BaseModel):
    disease_name: str = Field(min_length=1, max_length=255)
    confidence_score: float = Field(ge=0, le=1)
    severity: str = Field(min_length=1, max_length=32)
    possible_causes: list[str] = Field(default_factory=list)
    organic_treatment: list[str] = Field(default_factory=list)
    chemical_treatment: list[str] = Field(default_factory=list)
    prevention_steps: list[str] = Field(default_factory=list)
    escalate_to_human: bool

    @field_validator(
        "possible_causes",
        "organic_treatment",
        "chemical_treatment",
        "prevention_steps",
    )
    @classmethod
    def strip_list_values(cls, values: list[str]) -> list[str]:
        cleaned_values = [value.strip() for value in values if value.strip()]
        return cleaned_values


class DiagnosisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farm_id: uuid.UUID
    crop_image_id: uuid.UUID
    disease_name: str
    confidence_score: float
    severity: str
    possible_causes: list[str]
    organic_treatment: list[str]
    chemical_treatment: list[str]
    prevention_steps: list[str]
    escalate_to_human: bool
    raw_vision_output: dict[str, Any]
    created_at: datetime
