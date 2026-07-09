from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class WeatherLocationRead(BaseModel):
    name: str
    latitude: float
    longitude: float
    timezone: str
    country: Optional[str] = None
    admin1: Optional[str] = None
    admin2: Optional[str] = None


class CurrentWeatherRead(BaseModel):
    time: str
    temperature_c: Optional[float] = None
    apparent_temperature_c: Optional[float] = None
    relative_humidity_percent: Optional[int] = None
    precipitation_mm: Optional[float] = None
    rain_mm: Optional[float] = None
    weather_code: Optional[int] = None
    condition: str
    cloud_cover_percent: Optional[int] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_degrees: Optional[int] = None
    wind_gusts_kmh: Optional[float] = None


class DailyWeatherRead(BaseModel):
    date: date
    weather_code: Optional[int] = None
    condition: str
    temperature_max_c: Optional[float] = None
    temperature_min_c: Optional[float] = None
    apparent_temperature_max_c: Optional[float] = None
    apparent_temperature_min_c: Optional[float] = None
    precipitation_sum_mm: Optional[float] = None
    precipitation_probability_max_percent: Optional[int] = None
    relative_humidity_mean_percent: Optional[int] = None
    wind_speed_max_kmh: Optional[float] = None
    wind_gusts_max_kmh: Optional[float] = None


class FarmWeatherAdviceRead(BaseModel):
    irrigation: list[str]
    rainfall: list[str]
    spraying: list[str]
    heat: list[str]
    wind: list[str]
    humidity: list[str]


class FarmWeatherRead(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    crop: str
    resolved_location: WeatherLocationRead
    current: CurrentWeatherRead
    forecast: list[DailyWeatherRead]
    advice: FarmWeatherAdviceRead
    source: str
    fetched_at: datetime
