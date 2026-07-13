from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


SUPPORTED_THEMES = {"light", "dark", "system"}
SUPPORTED_UNITS = {"metric", "imperial"}
SUPPORTED_DATE_FORMATS = {"dd-mm-yyyy", "mm-dd-yyyy", "yyyy-mm-dd"}
SUPPORTED_EXPLANATION_DETAILS = {"concise", "standard", "detailed"}
SUPPORTED_LOCATION_SOURCES = {"current_location", "map_selection", "manual"}
SUPPORTED_LOCATION_PERMISSION_STATUSES = {
    "unknown",
    "unsupported",
    "prompt",
    "granted",
    "denied",
    "timeout",
    "unavailable",
}


DEFAULT_ACCOUNT_SETTINGS = {
    "units": "metric",
    "timezone": "Asia/Kolkata",
    "date_format": "dd-mm-yyyy",
    "theme": "system",
    "default_location": "",
    "default_location_latitude": None,
    "default_location_longitude": None,
    "location_source": "manual",
    "location_permission_status": "unknown",
    "response_language": "en",
    "ai_response_language": "en",
    "explanation_detail": "standard",
    "ai_explanation_detail": "standard",
    "organic_treatment_preference": True,
    "chemical_treatment_preference": True,
    "show_sources_by_default": False,
    "allow_farm_context_in_chat": True,
    "location_usage_consent": False,
    "ai_data_usage_explanation": (
        "Farm context is used to personalize agricultural guidance and is not "
        "used to change account permissions."
    ),
    "delete_account_requested": False,
    "export_account_data_requested": False,
}


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=255)
    phone_number: Optional[str] = Field(default=None, max_length=32)
    preferred_language: str = Field(default="en", min_length=2, max_length=16)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: Optional[EmailStr]
    phone_number: Optional[str]
    full_name: Optional[str]
    profile_picture_url: Optional[str] = None
    preferred_language: str
    role: str
    is_active: bool
    default_state: Optional[str] = None
    default_district: Optional[str] = None
    default_farm_id: Optional[uuid.UUID] = None
    account_settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class UserProfileRead(UserRead):
    pass


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Optional[str] = Field(default=None, max_length=255)
    phone_number: Optional[str] = Field(default=None, max_length=32)
    preferred_language: Optional[str] = Field(default=None, min_length=2, max_length=16)
    profile_picture_url: Optional[str] = Field(default=None, max_length=1024)
    default_state: Optional[str] = Field(default=None, max_length=100)
    default_district: Optional[str] = Field(default=None, max_length=100)
    default_farm_id: Optional[uuid.UUID] = None
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    units: Optional[Literal["metric", "imperial"]] = None
    theme: Optional[Literal["light", "dark", "system"]] = None

    @field_validator(
        "full_name",
        "phone_number",
        "preferred_language",
        "profile_picture_url",
        "default_state",
        "default_district",
        "timezone",
    )
    @classmethod
    def empty_text_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class AccountSettingsRead(BaseModel):
    preferred_language: str
    units: Literal["metric", "imperial"]
    timezone: str
    date_format: Literal["dd-mm-yyyy", "mm-dd-yyyy", "yyyy-mm-dd"]
    theme: Literal["light", "dark", "system"]
    default_state: Optional[str] = None
    default_district: Optional[str] = None
    default_farm_id: Optional[uuid.UUID] = None
    default_location: str
    default_location_latitude: Optional[float] = None
    default_location_longitude: Optional[float] = None
    location_source: str
    location_permission_status: str
    weather_alerts: bool = True
    irrigation_reminders: bool = True
    fertilizer_reminders: bool = True
    disease_alerts: bool = True
    crop_stage_reminders: bool = True
    high_risk_alerts: bool = True
    daily_summary: bool = True
    weekly_summary: bool = True
    push_enabled: bool = False
    push_token: Optional[str] = None
    push_platform: Optional[str] = None
    push_provider: Optional[str] = None
    response_language: str
    ai_response_language: str
    explanation_detail: Literal["concise", "standard", "detailed"]
    ai_explanation_detail: Literal["concise", "standard", "detailed"]
    organic_treatment_preference: bool
    chemical_treatment_preference: bool
    show_sources_by_default: bool
    allow_farm_context_in_chat: bool
    location_usage_consent: bool
    ai_data_usage_explanation: str
    delete_account_requested: bool
    export_account_data_requested: bool


class AccountSettingsUpdate(BaseModel):
    preferred_language: Optional[str] = Field(default=None, min_length=2, max_length=16)
    units: Optional[Literal["metric", "imperial"]] = None
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    date_format: Optional[Literal["dd-mm-yyyy", "mm-dd-yyyy", "yyyy-mm-dd"]] = None
    theme: Optional[Literal["light", "dark", "system"]] = None
    default_state: Optional[str] = Field(default=None, max_length=100)
    default_district: Optional[str] = Field(default=None, max_length=100)
    default_farm_id: Optional[uuid.UUID] = None
    default_location: Optional[str] = Field(default=None, max_length=255)
    default_location_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    default_location_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    location_source: Optional[str] = Field(default=None, max_length=32)
    location_permission_status: Optional[str] = Field(default=None, max_length=32)
    weather_alerts: Optional[bool] = None
    irrigation_reminders: Optional[bool] = None
    fertilizer_reminders: Optional[bool] = None
    disease_alerts: Optional[bool] = None
    crop_stage_reminders: Optional[bool] = None
    high_risk_alerts: Optional[bool] = None
    daily_summary: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    push_enabled: Optional[bool] = None
    push_token: Optional[str] = Field(default=None, max_length=512)
    push_platform: Optional[str] = Field(default=None, max_length=32)
    push_provider: Optional[str] = Field(default=None, max_length=32)
    response_language: Optional[str] = Field(default=None, min_length=2, max_length=16)
    ai_response_language: Optional[str] = Field(default=None, min_length=2, max_length=16)
    explanation_detail: Optional[Literal["concise", "standard", "detailed"]] = None
    ai_explanation_detail: Optional[Literal["concise", "standard", "detailed"]] = None
    organic_treatment_preference: Optional[bool] = None
    chemical_treatment_preference: Optional[bool] = None
    show_sources_by_default: Optional[bool] = None
    allow_farm_context_in_chat: Optional[bool] = None
    location_usage_consent: Optional[bool] = None
    delete_account_requested: Optional[bool] = None
    export_account_data_requested: Optional[bool] = None

    @field_validator(
        "preferred_language",
        "timezone",
        "default_state",
        "default_district",
        "default_location",
        "location_source",
        "location_permission_status",
        "push_token",
        "push_platform",
        "push_provider",
        "response_language",
        "ai_response_language",
    )
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return " ".join(value.split()) or None

    @field_validator("location_source")
    @classmethod
    def validate_location_source(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SUPPORTED_LOCATION_SOURCES:
            raise ValueError("location_source is invalid")
        return value

    @field_validator("location_permission_status")
    @classmethod
    def validate_location_permission_status(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SUPPORTED_LOCATION_PERMISSION_STATUSES:
            raise ValueError("location_permission_status is invalid")
        return value


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordChangeResponse(BaseModel):
    changed: bool = True


class AdminUserRead(UserRead):
    pass
