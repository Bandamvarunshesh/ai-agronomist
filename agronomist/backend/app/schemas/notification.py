from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


SUPPORTED_NOTIFICATION_TYPE_LIST = (
    "weather_alert",
    "irrigation_reminder",
    "fertilizer_reminder",
    "disease_alert",
    "crop_stage_reminder",
    "farming_task_reminder",
    "daily_ai_summary",
    "weekly_ai_summary",
    "high_risk_alert",
    "recommendation_generated",
    "farm_health_alert",
)

SUPPORTED_NOTIFICATION_TYPES = set(SUPPORTED_NOTIFICATION_TYPE_LIST)

DEFAULT_ENABLED_NOTIFICATION_TYPES = {
    notification_type: True for notification_type in SUPPORTED_NOTIFICATION_TYPE_LIST
}

QUIET_HOUR_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    farm_id: Optional[uuid.UUID]
    diagnosis_id: Optional[uuid.UUID]
    notification_type: str
    title: str
    body: str
    priority: str
    channel: str
    is_read: bool
    read_at: Optional[datetime]
    scheduled_for: Optional[datetime]
    sent_at: Optional[datetime]
    payload: dict[str, Any]
    source: str
    dedupe_key: Optional[str]
    deep_link: Optional[str]
    push_title: Optional[str]
    push_body: Optional[str]
    push_data: dict[str, Any]
    delivery_status: str
    delivery_error: Optional[str]
    created_at: datetime
    updated_at: datetime


class NotificationPreferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    notifications_enabled: bool
    in_app_enabled: bool
    push_enabled: bool
    email_enabled: bool
    sms_enabled: bool
    enabled_types: dict[str, bool]
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    timezone: str
    push_token: Optional[str]
    push_platform: Optional[str]
    push_provider: Optional[str]
    device_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NotificationPreferenceUpdate(BaseModel):
    notifications_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    enabled_types: Optional[dict[str, bool]] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = Field(default=None, max_length=5)
    quiet_hours_end: Optional[str] = Field(default=None, max_length=5)
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    push_token: Optional[str] = Field(default=None, max_length=512)
    push_platform: Optional[str] = Field(default=None, max_length=32)
    push_provider: Optional[str] = Field(default=None, max_length=32)
    device_metadata: Optional[dict[str, Any]] = None

    @field_validator("enabled_types")
    @classmethod
    def validate_enabled_types(
        cls,
        value: Optional[dict[str, bool]],
    ) -> Optional[dict[str, bool]]:
        if value is None:
            return None

        unknown_types = set(value) - SUPPORTED_NOTIFICATION_TYPES
        if unknown_types:
            unknown = ", ".join(sorted(unknown_types))
            raise ValueError(f"Unsupported notification types: {unknown}")
        return {key: bool(enabled) for key, enabled in value.items()}

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def validate_quiet_hour(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not QUIET_HOUR_PATTERN.match(value):
            raise ValueError("Quiet hours must use HH:MM 24-hour format")
        return value

    @field_validator("timezone", "push_token", "push_platform", "push_provider")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None
