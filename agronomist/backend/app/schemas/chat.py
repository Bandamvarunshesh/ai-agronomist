from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatSessionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    farm_id: Optional[uuid.UUID] = None
    title: Optional[str] = Field(default=None, max_length=255)
    channel: str = Field(default="web", min_length=1, max_length=32)

    @field_validator("title")
    @classmethod
    def empty_title_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value == "":
            return None
        return value


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    farm_id: Optional[uuid.UUID]
    title: Optional[str]
    channel: str
    status: str
    session_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=10000)


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    role: str
    content: str
    message_metadata: dict[str, Any]
    sent_at: datetime
    created_at: datetime
    updated_at: datetime


class ChatMessageExchangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
