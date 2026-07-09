from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


ESCALATION_CONTACT_TYPES = {
    "kvk",
    "agronomist",
    "govt_extension",
    "vet",
    "emergency",
}
ESCALATION_PRIORITIES = {"low", "normal", "high", "urgent"}
ESCALATION_TYPES = {"diagnosis", "chat", "manual"}


class EscalationContactBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    contact_type: str = Field(min_length=1, max_length=32)
    role: Optional[str] = Field(default=None, max_length=100)
    organization: Optional[str] = Field(default=None, max_length=255)
    district: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=32)
    email: Optional[str] = Field(default=None, max_length=255)
    preferred_channel: str = Field(default="phone", min_length=1, max_length=32)
    is_active: bool = True
    contact_priority: int = Field(default=100, ge=0)
    is_fallback: bool = False
    notes: Optional[str] = None
    service_area: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_contact(self):
        if self.contact_type not in ESCALATION_CONTACT_TYPES:
            raise ValueError("Unsupported escalation contact type")
        if not self.phone_number and not self.email:
            raise ValueError("At least one of phone_number or email is required")
        return self


class EscalationContactCreate(EscalationContactBase):
    pass


class EscalationContactUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    contact_type: Optional[str] = Field(default=None, min_length=1, max_length=32)
    role: Optional[str] = Field(default=None, max_length=100)
    organization: Optional[str] = Field(default=None, max_length=255)
    district: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=32)
    email: Optional[str] = Field(default=None, max_length=255)
    preferred_channel: Optional[str] = Field(default=None, min_length=1, max_length=32)
    is_active: Optional[bool] = None
    contact_priority: Optional[int] = Field(default=None, ge=0)
    is_fallback: Optional[bool] = None
    notes: Optional[str] = None
    service_area: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_contact_type(self):
        if self.contact_type is not None and self.contact_type not in ESCALATION_CONTACT_TYPES:
            raise ValueError("Unsupported escalation contact type")
        return self


class EscalationContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    farm_id: Optional[uuid.UUID]
    name: str
    contact_type: str
    role: Optional[str]
    organization: Optional[str]
    district: Optional[str]
    state: Optional[str]
    phone_number: Optional[str]
    email: Optional[str]
    preferred_channel: str
    is_active: bool
    contact_priority: int
    is_fallback: bool
    notes: Optional[str]
    service_area: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EscalationContactLookupRead(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    district: str
    state: str
    requested_contact_type: Optional[str]
    routing_level: str
    fallback_used: bool
    contact: EscalationContactRead


class EscalationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    farm_id: uuid.UUID
    diagnosis_id: Optional[uuid.UUID] = None
    chat_session_id: Optional[uuid.UUID] = None
    escalation_type: Optional[str] = None
    contact_type_requested: Optional[str] = Field(default=None, max_length=32)
    priority: str = Field(default="normal", min_length=1, max_length=32)
    subject: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None

    @model_validator(mode="after")
    def validate_escalation(self):
        if self.priority not in ESCALATION_PRIORITIES:
            raise ValueError("Unsupported escalation priority")
        if (
            self.contact_type_requested is not None
            and self.contact_type_requested not in ESCALATION_CONTACT_TYPES
        ):
            raise ValueError("Unsupported escalation contact type")
        if self.escalation_type is not None and self.escalation_type not in ESCALATION_TYPES:
            raise ValueError("Unsupported escalation type")
        if self.diagnosis_id is not None and self.chat_session_id is not None:
            raise ValueError("Use either diagnosis_id or chat_session_id, not both")
        if self.escalation_type == "diagnosis" and self.diagnosis_id is None:
            raise ValueError("diagnosis_id is required for diagnosis escalation")
        if self.escalation_type == "chat" and self.chat_session_id is None:
            raise ValueError("chat_session_id is required for chat escalation")
        if self.escalation_type == "manual" and (
            self.diagnosis_id is not None or self.chat_session_id is not None
        ):
            raise ValueError("manual escalation cannot include diagnosis_id or chat_session_id")
        return self


class EscalationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farm_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    diagnosis_id: Optional[uuid.UUID]
    chat_session_id: Optional[uuid.UUID]
    contact_id: Optional[uuid.UUID]
    escalation_type: str
    contact_type_requested: Optional[str]
    status: str
    priority: str
    subject: str
    description: Optional[str]
    resolution_notes: Optional[str]
    routing_status: str
    routing_reason: Optional[str]
    fallback_used: bool
    contact_snapshot: dict[str, Any]
    escalated_at: datetime
    resolved_at: Optional[datetime]
    escalation_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    contact: Optional[EscalationContactRead] = None
