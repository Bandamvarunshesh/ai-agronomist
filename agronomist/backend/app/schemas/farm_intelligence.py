from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.weather import CurrentWeatherRead, DailyWeatherRead, WeatherLocationRead


class ProviderHealthRead(BaseModel):
    provider: str
    provider_type: str
    status: str
    detail: str | None = None
    checked_at: datetime
    latency_ms: int | None = None
    consecutive_failures: int = 0


class GovernmentAdvisoryRead(BaseModel):
    source_name: str
    title: str
    summary: str | None = None
    category: str | None = None
    url: str
    published_at: datetime | None = None
    crop_tags: list[str] = Field(default_factory=list)
    state_tags: list[str] = Field(default_factory=list)
    district_tags: list[str] = Field(default_factory=list)
    relevance_score: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class FarmNewsItemRead(BaseModel):
    source_name: str
    title: str
    summary: str | None = None
    category: str | None = None
    url: str
    published_at: datetime | None = None
    crop_tags: list[str] = Field(default_factory=list)
    state_tags: list[str] = Field(default_factory=list)
    district_tags: list[str] = Field(default_factory=list)
    relevance_score: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketIntelligenceRead(BaseModel):
    source_name: str
    crop: str
    market: str
    district: str | None = None
    state: str | None = None
    price: float | None = None
    arrivals: float | None = None
    trend: str | None = None
    unit: str | None = None
    observed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SoilIntelligenceRead(BaseModel):
    source_name: str
    soil_type: str | None = None
    ph: float | None = None
    organic_carbon: float | None = None
    nutrient_estimates: dict[str, float | str | None] = Field(default_factory=dict)
    texture: str | None = None
    observed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskAlertRead(BaseModel):
    source_name: str
    alert_type: str
    title: str
    summary: str | None = None
    severity: str
    affected_districts: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    url: str
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FarmRiskRead(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    crop: str
    risk_score: float
    pest_alerts: list[RiskAlertRead] = Field(default_factory=list)
    disease_alerts: list[RiskAlertRead] = Field(default_factory=list)
    provider_health: list[ProviderHealthRead] = Field(default_factory=list)
    unavailable: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime


class FarmIntelligenceRead(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    crop: str
    resolved_location: WeatherLocationRead | None = None
    weather: CurrentWeatherRead | None = None
    forecast: list[DailyWeatherRead] = Field(default_factory=list)
    soil: SoilIntelligenceRead | None = None
    market: list[MarketIntelligenceRead] = Field(default_factory=list)
    government_advisories: list[GovernmentAdvisoryRead] = Field(default_factory=list)
    news: list[FarmNewsItemRead] = Field(default_factory=list)
    pest_alerts: list[RiskAlertRead] = Field(default_factory=list)
    disease_alerts: list[RiskAlertRead] = Field(default_factory=list)
    risk_score: float
    provider_health: list[ProviderHealthRead] = Field(default_factory=list)
    unavailable: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime


class WeatherIntelligenceRead(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    crop: str
    resolved_location: WeatherLocationRead | None = None
    weather: CurrentWeatherRead | None = None
    forecast: list[DailyWeatherRead] = Field(default_factory=list)
    provider_health: list[ProviderHealthRead] = Field(default_factory=list)
    unavailable: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime


class MarketIntelligenceResponseRead(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    crop: str
    market: list[MarketIntelligenceRead] = Field(default_factory=list)
    provider_health: list[ProviderHealthRead] = Field(default_factory=list)
    unavailable: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime


class AdvisoryIntelligenceResponseRead(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    crop: str
    government_advisories: list[GovernmentAdvisoryRead] = Field(default_factory=list)
    provider_health: list[ProviderHealthRead] = Field(default_factory=list)
    unavailable: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime


class NewsIntelligenceResponseRead(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    crop: str
    news: list[FarmNewsItemRead] = Field(default_factory=list)
    provider_health: list[ProviderHealthRead] = Field(default_factory=list)
    unavailable: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime


class SoilIntelligenceResponseRead(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    crop: str
    soil: SoilIntelligenceRead | None = None
    provider_health: list[ProviderHealthRead] = Field(default_factory=list)
    unavailable: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime
