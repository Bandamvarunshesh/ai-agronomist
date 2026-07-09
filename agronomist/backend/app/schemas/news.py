from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class NewsArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: Optional[uuid.UUID]
    source_name: str
    article_type: str
    title: str
    summary: Optional[str]
    content: Optional[str]
    url: str
    language: str
    category: Optional[str]
    crop_tags: list[str]
    state_tags: list[str]
    district_tags: list[str]
    credibility_score: Decimal
    content_hash: str
    published_at: Optional[datetime]
    fetched_at: datetime
    article_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class IntelligenceSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    source_format: str
    url: str
    language: str
    country: Optional[str]
    state: Optional[str]
    district: Optional[str]
    crop_tags: list[str]
    credibility_score: Decimal
    is_active: bool
    last_synced_at: Optional[datetime]
    source_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class IntelligenceSourceConfigEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=255)
    source_type: Literal["news", "government_advisory", "research", "market_update"]
    source_format: Literal["rss", "atom", "xml", "json", "html"] = "rss"
    url: str = Field(min_length=1, max_length=2048)
    language: str = Field(default="en", min_length=1, max_length=16)
    country: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    district: Optional[str] = Field(default=None, max_length=100)
    crop_tags: list[str] = Field(default_factory=list)
    credibility_score: Decimal = Field(default=Decimal("0.5000"), ge=0, le=1)
    is_active: bool = True
    source_metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("source_metadata", "metadata"),
    )


class IntelligenceSourceConfigLoadResponse(BaseModel):
    config_path: str
    dry_run: bool
    source_count: int
    upserted_count: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IntelligenceSourceSyncReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: Optional[uuid.UUID]
    source_name: str
    source_url: str
    source_type: str
    source_format: str
    dry_run: bool
    fetched: bool
    parsed_count: int
    duplicate_count: int
    would_create_count: int
    created_count: int
    status: str
    error: Optional[str] = None


class IntelligenceSourceSyncResponse(BaseModel):
    dry_run: bool
    source_count: int
    created_count: int
    reports: list[IntelligenceSourceSyncReportRead]
