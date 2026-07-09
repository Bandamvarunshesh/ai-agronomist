from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.farm import Farm
from app.models.intelligence import IntelligenceSource, NewsArticle
from app.repositories.intelligence_repository import IntelligenceRepository
from app.schemas.farm_intelligence import (
    AdvisoryIntelligenceResponseRead,
    FarmIntelligenceRead,
    FarmNewsItemRead,
    FarmRiskRead,
    GovernmentAdvisoryRead,
    MarketIntelligenceRead,
    MarketIntelligenceResponseRead,
    NewsIntelligenceResponseRead,
    ProviderHealthRead,
    RiskAlertRead,
    SoilIntelligenceRead,
    SoilIntelligenceResponseRead,
    WeatherIntelligenceRead,
)
from app.schemas.weather import (
    CurrentWeatherRead,
    DailyWeatherRead,
    FarmWeatherAdviceRead,
    FarmWeatherRead,
    WeatherLocationRead,
)
from app.services.cache_service import TTLCache
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    IntelligencePersistenceError,
    IntelligenceSourceError,
    WeatherLocationNotFoundError,
    WeatherProviderError,
    WeatherResponseParseError,
)
from app.services.farm_service import FarmService
from app.services.intelligence_service import IntelligenceService, ParsedArticle


logger = logging.getLogger(__name__)

CURRENT_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]

DAILY_VARIABLES = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "relative_humidity_2m_mean",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
]

WEATHER_CODE_LABELS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

ARTICLE_SOURCE_TYPES = {"news", "government_advisory", "research"}
ALERT_SOURCE_TYPES = {"pest_alert", "disease_alert", "outbreak_alert"}

weather_cache: TTLCache[WeatherIntelligenceRead] = TTLCache(
    settings.farm_weather_cache_ttl_seconds,
)
market_cache: TTLCache[MarketIntelligenceResponseRead] = TTLCache(
    settings.farm_market_cache_ttl_seconds,
)
advisory_cache: TTLCache[AdvisoryIntelligenceResponseRead] = TTLCache(
    settings.farm_advisory_cache_ttl_seconds,
)
soil_cache: TTLCache[SoilIntelligenceResponseRead] = TTLCache(
    settings.farm_soil_cache_ttl_seconds,
)
news_cache: TTLCache[NewsIntelligenceResponseRead] = TTLCache(
    settings.farm_news_cache_ttl_seconds,
)
risk_cache: TTLCache[FarmRiskRead] = TTLCache(settings.farm_risk_cache_ttl_seconds)
provider_health_cache: TTLCache[ProviderHealthRead] = TTLCache(86400)


@dataclass(frozen=True)
class WeatherBundle:
    location: WeatherLocationRead
    current: CurrentWeatherRead
    forecast: list[DailyWeatherRead]
    provider: str


class BaseProviderAdapter:
    provider_name = "provider"
    provider_type = "external"

    def _fetch_json(self, url: str) -> dict[str, Any]:
        payload = self._fetch_json_any(url)
        if not isinstance(payload, dict):
            raise IntelligenceSourceError(
                f"{self.provider_name} returned a non-object JSON payload",
            )
        return payload

    def _fetch_json_any(self, url: str) -> Any:
        latency_ms = None
        last_error: Exception | None = None
        started = time.monotonic()

        for attempt in range(settings.intelligence_request_retries):
            try:
                request = Request(url, headers={"User-Agent": "ai-agronomist/0.1"})
                with urlopen(
                    request,
                    timeout=settings.intelligence_request_timeout_seconds,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                latency_ms = int((time.monotonic() - started) * 1000)
                self._record_health("healthy", latency_ms=latency_ms)
                return payload
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                backoff_seconds = min(2**attempt, 8)
                logger.warning(
                    "Provider request failed: provider=%s type=%s url=%s attempt=%s backoff_seconds=%s error=%s",
                    self.provider_name,
                    self.provider_type,
                    url,
                    attempt + 1,
                    backoff_seconds,
                    str(exc),
                )
                if attempt < settings.intelligence_request_retries - 1:
                    time.sleep(backoff_seconds)

        latency_ms = int((time.monotonic() - started) * 1000)
        self._record_health(
            "unhealthy",
            detail=str(last_error) if last_error else "request failed",
            latency_ms=latency_ms,
        )
        raise IntelligenceSourceError(
            f"{self.provider_name} request failed",
        ) from last_error

    def _record_health(
        self,
        status: str,
        *,
        detail: str | None = None,
        latency_ms: int | None = None,
    ) -> None:
        cache_key = f"{self.provider_type}:{self.provider_name}"
        previous = provider_health_cache.get_stale(cache_key)
        consecutive_failures = 0
        if status != "healthy":
            consecutive_failures = (previous.consecutive_failures if previous else 0) + 1

        health = ProviderHealthRead(
            provider=self.provider_name,
            provider_type=self.provider_type,
            status=status,
            detail=detail,
            checked_at=datetime.now(timezone.utc),
            latency_ms=latency_ms,
            consecutive_failures=consecutive_failures,
        )
        provider_health_cache.set(cache_key, health)
        logger.info(
            "Provider health: provider=%s type=%s status=%s latency_ms=%s consecutive_failures=%s detail=%s",
            health.provider,
            health.provider_type,
            health.status,
            health.latency_ms,
            health.consecutive_failures,
            health.detail,
        )

    def health(self) -> ProviderHealthRead | None:
        return provider_health_cache.get_stale(
            f"{self.provider_type}:{self.provider_name}",
        )


class OpenMeteoWeatherAdapter(BaseProviderAdapter):
    provider_name = "open-meteo"
    provider_type = "weather"

    def resolve_location(self, farm: Farm) -> WeatherLocationRead:
        for query in self._build_location_queries(farm):
            payload = self._fetch_json(
                f"{settings.open_meteo_geocoding_url}?{urlencode({'name': query, 'count': 1, 'language': 'en', 'format': 'json'})}",
            )
            result = self._first_geocoding_result(payload)
            if result is None:
                continue

            latitude = self._optional_float(result.get("latitude"))
            longitude = self._optional_float(result.get("longitude"))
            if latitude is None or longitude is None:
                raise WeatherResponseParseError(
                    "Open-Meteo geocoding response is missing coordinates",
                )

            return WeatherLocationRead(
                name=str(result.get("name") or query),
                latitude=latitude,
                longitude=longitude,
                timezone=str(result.get("timezone") or "auto"),
                country=result.get("country"),
                admin1=result.get("admin1"),
                admin2=result.get("admin2"),
            )

        raise WeatherLocationNotFoundError(
            "Unable to resolve farm location for weather lookup",
        )

    def fetch_weather(self, farm: Farm) -> WeatherBundle:
        location = self.resolve_location(farm)
        payload = self._fetch_json(
            f"{settings.open_meteo_forecast_url}?{urlencode({'latitude': location.latitude, 'longitude': location.longitude, 'current': ','.join(CURRENT_VARIABLES), 'daily': ','.join(DAILY_VARIABLES), 'forecast_days': 7, 'timezone': location.timezone or 'auto', 'temperature_unit': 'celsius', 'wind_speed_unit': 'kmh', 'precipitation_unit': 'mm'})}",
        )
        return WeatherBundle(
            location=location,
            current=_build_current_from_open_meteo(payload),
            forecast=_build_forecast_from_open_meteo(payload),
            provider="Open-Meteo",
        )

    def _build_location_queries(self, farm: Farm) -> list[str]:
        candidates = [
            ", ".join(
                part
                for part in [farm.location, farm.village, farm.district, farm.state]
                if part
            ),
            ", ".join(part for part in [farm.village, farm.district, farm.state] if part),
            ", ".join(part for part in [farm.district, farm.state] if part),
            farm.location,
            farm.village,
            farm.district,
        ]
        queries: list[str] = []
        for candidate in candidates:
            normalized = " ".join(candidate.split())
            if normalized and normalized not in queries:
                queries.append(normalized)
        return queries

    def _first_geocoding_result(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return None
        result = results[0]
        if not isinstance(result, dict):
            return None
        return result

    def _optional_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise WeatherResponseParseError(
                "Open-Meteo response contains invalid numeric data",
            ) from exc


class OpenWeatherWeatherAdapter(BaseProviderAdapter):
    provider_name = "openweather"
    provider_type = "weather"

    def is_configured(self) -> bool:
        return bool(settings.openweather_api_key.strip())

    def fetch_weather(self, farm: Farm) -> WeatherBundle:
        if not self.is_configured():
            raise IntelligenceSourceError("OpenWeather is not configured")

        location = self._resolve_location(farm)
        payload = self._fetch_json(
            f"{settings.openweather_forecast_url}?{urlencode({'lat': location.latitude, 'lon': location.longitude, 'appid': settings.openweather_api_key, 'units': 'metric'})}",
        )
        current, forecast = self._parse_forecast(payload)
        return WeatherBundle(
            location=location,
            current=current,
            forecast=forecast,
            provider="OpenWeather",
        )

    def _resolve_location(self, farm: Farm) -> WeatherLocationRead:
        query = ", ".join(part for part in [farm.village, farm.district, farm.state] if part)
        payload = self._fetch_json_any(
            f"{settings.openweather_geocoding_url}?{urlencode({'q': query, 'limit': 1, 'appid': settings.openweather_api_key})}",
        )
        if not isinstance(payload, list):
            raise WeatherResponseParseError("OpenWeather geocoding returned invalid data")
        if not payload:
            raise WeatherLocationNotFoundError("Unable to resolve farm location for weather lookup")
        result = payload[0]
        if not isinstance(result, dict):
            raise WeatherResponseParseError("OpenWeather geocoding returned invalid data")
        lat = result.get("lat")
        lon = result.get("lon")
        if lat is None or lon is None:
            raise WeatherResponseParseError("OpenWeather geocoding response is missing coordinates")
        return WeatherLocationRead(
            name=str(result.get("name") or query),
            latitude=float(lat),
            longitude=float(lon),
            timezone="auto",
            country=result.get("country"),
            admin1=result.get("state"),
            admin2=farm.district,
        )

    def _parse_forecast(
        self,
        payload: dict[str, Any],
    ) -> tuple[CurrentWeatherRead, list[DailyWeatherRead]]:
        rows = payload.get("list")
        if not isinstance(rows, list) or not rows:
            raise WeatherResponseParseError("OpenWeather response is missing forecast rows")

        first = rows[0]
        if not isinstance(first, dict):
            raise WeatherResponseParseError("OpenWeather response is invalid")
        current = CurrentWeatherRead(
            time=str(first.get("dt_txt") or ""),
            temperature_c=_optional_float(_nested_value(first, "main", "temp")),
            apparent_temperature_c=_optional_float(_nested_value(first, "main", "feels_like")),
            relative_humidity_percent=_optional_int(_nested_value(first, "main", "humidity")),
            precipitation_mm=_optional_float(_nested_value(first, "rain", "3h")),
            rain_mm=_optional_float(_nested_value(first, "rain", "3h")),
            weather_code=_optional_int(_nested_value(_first_list_item(first.get("weather")), "id")),
            condition=str(_nested_value(_first_list_item(first.get("weather")), "description") or "Unknown").title(),
            cloud_cover_percent=_optional_int(_nested_value(first, "clouds", "all")),
            wind_speed_kmh=_meters_per_second_to_kmh(_optional_float(_nested_value(first, "wind", "speed"))),
            wind_direction_degrees=_optional_int(_nested_value(first, "wind", "deg")),
            wind_gusts_kmh=_meters_per_second_to_kmh(_optional_float(_nested_value(first, "wind", "gust"))),
        )

        per_day: dict[date, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            timestamp = _parse_datetime(row.get("dt_txt") or row.get("dt"))
            if timestamp is None:
                continue
            day_key = timestamp.date()
            bucket = per_day.setdefault(
                day_key,
                {
                    "temps_max": [],
                    "temps_min": [],
                    "feels_max": [],
                    "feels_min": [],
                    "rain": [],
                    "humidity": [],
                    "wind": [],
                    "gusts": [],
                    "weather_id": None,
                    "condition": None,
                },
            )
            temp = _optional_float(_nested_value(row, "main", "temp"))
            feels = _optional_float(_nested_value(row, "main", "feels_like"))
            humidity = _optional_int(_nested_value(row, "main", "humidity"))
            rain = _optional_float(_nested_value(row, "rain", "3h"))
            wind = _meters_per_second_to_kmh(_optional_float(_nested_value(row, "wind", "speed")))
            gust = _meters_per_second_to_kmh(_optional_float(_nested_value(row, "wind", "gust")))
            weather_obj = _first_list_item(row.get("weather"))
            weather_id = _optional_int(_nested_value(weather_obj, "id"))
            condition = _nested_value(weather_obj, "description")
            if temp is not None:
                bucket["temps_max"].append(temp)
                bucket["temps_min"].append(temp)
            if feels is not None:
                bucket["feels_max"].append(feels)
                bucket["feels_min"].append(feels)
            if rain is not None:
                bucket["rain"].append(rain)
            if humidity is not None:
                bucket["humidity"].append(humidity)
            if wind is not None:
                bucket["wind"].append(wind)
            if gust is not None:
                bucket["gusts"].append(gust)
            bucket["weather_id"] = weather_id or bucket["weather_id"]
            bucket["condition"] = str(condition).title() if condition else bucket["condition"]

        forecast: list[DailyWeatherRead] = []
        for day_key in sorted(per_day.keys())[:7]:
            bucket = per_day[day_key]
            forecast.append(
                DailyWeatherRead(
                    date=day_key,
                    weather_code=bucket["weather_id"],
                    condition=str(bucket["condition"] or "Unknown"),
                    temperature_max_c=max(bucket["temps_max"]) if bucket["temps_max"] else None,
                    temperature_min_c=min(bucket["temps_min"]) if bucket["temps_min"] else None,
                    apparent_temperature_max_c=max(bucket["feels_max"]) if bucket["feels_max"] else None,
                    apparent_temperature_min_c=min(bucket["feels_min"]) if bucket["feels_min"] else None,
                    precipitation_sum_mm=sum(bucket["rain"]) if bucket["rain"] else None,
                    precipitation_probability_max_percent=None,
                    relative_humidity_mean_percent=int(sum(bucket["humidity"]) / len(bucket["humidity"])) if bucket["humidity"] else None,
                    wind_speed_max_kmh=max(bucket["wind"]) if bucket["wind"] else None,
                    wind_gusts_max_kmh=max(bucket["gusts"]) if bucket["gusts"] else None,
                )
            )
        if not forecast:
            raise WeatherResponseParseError("OpenWeather response contains no forecast days")
        return current, forecast


class WeatherAPIWeatherAdapter(BaseProviderAdapter):
    provider_name = "weatherapi"
    provider_type = "weather"

    def is_configured(self) -> bool:
        return bool(settings.weatherapi_api_key.strip())

    def fetch_weather(self, farm: Farm) -> WeatherBundle:
        if not self.is_configured():
            raise IntelligenceSourceError("WeatherAPI is not configured")

        query = ", ".join(part for part in [farm.village, farm.district, farm.state] if part)
        payload = self._fetch_json(
            f"{settings.weatherapi_base_url.rstrip('/')}/forecast.json?{urlencode({'key': settings.weatherapi_api_key, 'q': query, 'days': 7, 'aqi': 'no', 'alerts': 'no'})}",
        )
        location_payload = payload.get("location")
        current_payload = payload.get("current")
        forecast_payload = _nested_value(payload, "forecast", "forecastday")
        if not isinstance(location_payload, dict) or not isinstance(current_payload, dict) or not isinstance(forecast_payload, list):
            raise WeatherResponseParseError("WeatherAPI response is incomplete")
        location = WeatherLocationRead(
            name=str(location_payload.get("name") or query),
            latitude=float(location_payload.get("lat")),
            longitude=float(location_payload.get("lon")),
            timezone=str(location_payload.get("tz_id") or "auto"),
            country=location_payload.get("country"),
            admin1=location_payload.get("region"),
            admin2=farm.district,
        )
        current = CurrentWeatherRead(
            time=str(location_payload.get("localtime") or ""),
            temperature_c=_optional_float(current_payload.get("temp_c")),
            apparent_temperature_c=_optional_float(current_payload.get("feelslike_c")),
            relative_humidity_percent=_optional_int(current_payload.get("humidity")),
            precipitation_mm=_optional_float(current_payload.get("precip_mm")),
            rain_mm=_optional_float(current_payload.get("precip_mm")),
            weather_code=_optional_int(_nested_value(current_payload, "condition", "code")),
            condition=str(_nested_value(current_payload, "condition", "text") or "Unknown"),
            cloud_cover_percent=_optional_int(current_payload.get("cloud")),
            wind_speed_kmh=_optional_float(current_payload.get("wind_kph")),
            wind_direction_degrees=None,
            wind_gusts_kmh=_optional_float(current_payload.get("gust_kph")),
        )
        forecast: list[DailyWeatherRead] = []
        for day_payload in forecast_payload[:7]:
            if not isinstance(day_payload, dict):
                continue
            day_data = day_payload.get("day")
            if not isinstance(day_data, dict):
                continue
            try:
                forecast_date = date.fromisoformat(str(day_payload.get("date")))
            except ValueError as exc:
                raise WeatherResponseParseError("WeatherAPI returned an invalid forecast date") from exc
            forecast.append(
                DailyWeatherRead(
                    date=forecast_date,
                    weather_code=_optional_int(_nested_value(day_data, "condition", "code")),
                    condition=str(_nested_value(day_data, "condition", "text") or "Unknown"),
                    temperature_max_c=_optional_float(day_data.get("maxtemp_c")),
                    temperature_min_c=_optional_float(day_data.get("mintemp_c")),
                    apparent_temperature_max_c=_optional_float(day_data.get("maxtemp_c")),
                    apparent_temperature_min_c=_optional_float(day_data.get("mintemp_c")),
                    precipitation_sum_mm=_optional_float(day_data.get("totalprecip_mm")),
                    precipitation_probability_max_percent=_optional_int(day_data.get("daily_chance_of_rain")),
                    relative_humidity_mean_percent=_optional_int(day_data.get("avghumidity")),
                    wind_speed_max_kmh=_optional_float(day_data.get("maxwind_kph")),
                    wind_gusts_max_kmh=_optional_float(day_data.get("maxwind_kph")),
                )
            )
        if not forecast:
            raise WeatherResponseParseError("WeatherAPI response contains no forecast days")
        return WeatherBundle(
            location=location,
            current=current,
            forecast=forecast,
            provider="WeatherAPI",
        )


class FarmIntelligenceService:
    def __init__(self, db: Session):
        self.db = db
        self.farm_service = FarmService(db)
        self.repository = IntelligenceRepository(db)
        self.intelligence_service = IntelligenceService(db)
        self.weather_adapters = [
            OpenMeteoWeatherAdapter(),
            OpenWeatherWeatherAdapter(),
            WeatherAPIWeatherAdapter(),
        ]

    def get_farm_intelligence(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> FarmIntelligenceRead:
        farm = self._get_farm(user_id=user_id, farm_id=farm_id)
        weather = self._safe_weather_intelligence(user_id=user_id, farm_id=farm_id, farm=farm)
        market = self.get_market_intelligence(user_id=user_id, farm_id=farm_id, farm=farm)
        advisories = self.get_advisory_intelligence(user_id=user_id, farm_id=farm_id, farm=farm)
        news = self.get_news_intelligence(user_id=user_id, farm_id=farm_id, farm=farm)
        soil = self.get_soil_intelligence(user_id=user_id, farm_id=farm_id, farm=farm, location=weather.resolved_location)
        risk = self.get_risk_intelligence(
            user_id=user_id,
            farm_id=farm_id,
            farm=farm,
            weather=weather,
            advisories=advisories,
            news=news,
        )

        return FarmIntelligenceRead(
            farm_id=farm.id,
            farm_name=farm.farm_name,
            crop=farm.crop,
            resolved_location=weather.resolved_location,
            weather=weather.weather,
            forecast=weather.forecast,
            soil=soil.soil,
            market=market.market,
            government_advisories=advisories.government_advisories,
            news=news.news,
            pest_alerts=risk.pest_alerts,
            disease_alerts=risk.disease_alerts,
            risk_score=risk.risk_score,
            provider_health=self._merge_health(
                weather.provider_health,
                market.provider_health,
                advisories.provider_health,
                news.provider_health,
                soil.provider_health,
                risk.provider_health,
            ),
            unavailable=self._merge_unavailable(
                weather.unavailable,
                market.unavailable,
                advisories.unavailable,
                news.unavailable,
                soil.unavailable,
                risk.unavailable,
            ),
            generated_at=datetime.now(timezone.utc),
        )

    def get_weather_intelligence(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        farm: Farm | None = None,
    ) -> WeatherIntelligenceRead:
        farm = farm or self._get_farm(user_id=user_id, farm_id=farm_id)
        cache_key = f"{farm.id}"
        cached = weather_cache.get(cache_key)
        if cached is not None:
            return cached

        stale = weather_cache.get_stale(cache_key)
        failures: list[str] = []
        for adapter in self.weather_adapters:
            try:
                if hasattr(adapter, "is_configured") and not adapter.is_configured():
                    continue
                bundle = adapter.fetch_weather(farm)
                response = WeatherIntelligenceRead(
                    farm_id=farm.id,
                    farm_name=farm.farm_name,
                    crop=farm.crop,
                    resolved_location=bundle.location,
                    weather=bundle.current,
                    forecast=bundle.forecast,
                    provider_health=self._collect_provider_health(),
                    unavailable={},
                    generated_at=datetime.now(timezone.utc),
                )
                weather_cache.set(cache_key, response)
                return response
            except (
                IntelligenceSourceError,
                WeatherLocationNotFoundError,
                WeatherProviderError,
                WeatherResponseParseError,
            ) as exc:
                failures.append(f"{adapter.provider_name}: {exc}")
                logger.warning(
                    "Weather provider failed: provider=%s farm_id=%s error=%s",
                    adapter.provider_name,
                    farm.id,
                    str(exc),
                )

        if stale is not None:
            return stale.model_copy(
                update={
                    "provider_health": self._collect_provider_health(),
                    "unavailable": {"weather": "; ".join(failures) or "Using cached weather"},
                    "generated_at": datetime.now(timezone.utc),
                }
            )

        raise WeatherProviderError("; ".join(failures) or "No weather provider succeeded")

    def get_market_intelligence(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        farm: Farm | None = None,
    ) -> MarketIntelligenceResponseRead:
        farm = farm or self._get_farm(user_id=user_id, farm_id=farm_id)
        cache_key = f"{farm.id}"
        cached = market_cache.get(cache_key)
        if cached is not None:
            return cached

        stale = market_cache.get_stale(cache_key)
        unavailable: dict[str, str] = {}
        entries: list[MarketIntelligenceRead] = []
        try:
            sources = self._get_sources_by_type({"market_price"})
            entries = self._collect_market_entries(farm=farm, sources=sources)
        except IntelligencePersistenceError as exc:
            unavailable["market"] = str(exc)

        if entries:
            response = MarketIntelligenceResponseRead(
                farm_id=farm.id,
                farm_name=farm.farm_name,
                crop=farm.crop,
                market=entries,
                provider_health=self._collect_provider_health(),
                unavailable=unavailable,
                generated_at=datetime.now(timezone.utc),
            )
            market_cache.set(cache_key, response)
            return response
        if stale is not None:
            return stale.model_copy(
                update={
                    "provider_health": self._collect_provider_health(),
                    "unavailable": self._merge_unavailable(stale.unavailable, unavailable or {"market": "Using cached market intelligence"}),
                    "generated_at": datetime.now(timezone.utc),
                }
            )
        return MarketIntelligenceResponseRead(
            farm_id=farm.id,
            farm_name=farm.farm_name,
            crop=farm.crop,
            market=[],
            provider_health=self._collect_provider_health(),
            unavailable=unavailable or {"market": "No market provider data available"},
            generated_at=datetime.now(timezone.utc),
        )

    def get_advisory_intelligence(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        farm: Farm | None = None,
    ) -> AdvisoryIntelligenceResponseRead:
        farm = farm or self._get_farm(user_id=user_id, farm_id=farm_id)
        cache_key = f"{farm.id}"
        cached = advisory_cache.get(cache_key)
        if cached is not None:
            return cached

        stale = advisory_cache.get_stale(cache_key)
        unavailable: dict[str, str] = {}
        advisories = self._rank_archived_articles(
            farm=farm,
            article_types={"government_advisory"},
            limit=10,
        )
        if not advisories and stale is not None:
            return stale.model_copy(
                update={
                    "provider_health": self._collect_provider_health(),
                    "unavailable": {"advisories": "Using cached advisory intelligence"},
                    "generated_at": datetime.now(timezone.utc),
                }
            )

        response = AdvisoryIntelligenceResponseRead(
            farm_id=farm.id,
            farm_name=farm.farm_name,
            crop=farm.crop,
            government_advisories=[
                self._article_to_advisory(item, farm) for item in advisories
            ],
            provider_health=self._collect_provider_health(),
            unavailable=unavailable,
            generated_at=datetime.now(timezone.utc),
        )
        advisory_cache.set(cache_key, response)
        return response

    def get_news_intelligence(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        farm: Farm | None = None,
    ) -> NewsIntelligenceResponseRead:
        farm = farm or self._get_farm(user_id=user_id, farm_id=farm_id)
        cache_key = f"{farm.id}"
        cached = news_cache.get(cache_key)
        if cached is not None:
            return cached

        stale = news_cache.get_stale(cache_key)
        news_items = self._rank_archived_articles(
            farm=farm,
            article_types={"news", "research", "market_update"},
            limit=12,
        )
        if not news_items and stale is not None:
            return stale.model_copy(
                update={
                    "provider_health": self._collect_provider_health(),
                    "unavailable": {"news": "Using cached news intelligence"},
                    "generated_at": datetime.now(timezone.utc),
                }
            )

        response = NewsIntelligenceResponseRead(
            farm_id=farm.id,
            farm_name=farm.farm_name,
            crop=farm.crop,
            news=[self._article_to_news_item(item, farm) for item in news_items],
            provider_health=self._collect_provider_health(),
            unavailable={},
            generated_at=datetime.now(timezone.utc),
        )
        news_cache.set(cache_key, response)
        return response

    def get_soil_intelligence(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        farm: Farm | None = None,
        location: WeatherLocationRead | None = None,
    ) -> SoilIntelligenceResponseRead:
        farm = farm or self._get_farm(user_id=user_id, farm_id=farm_id)
        cache_key = f"{farm.id}"
        cached = soil_cache.get(cache_key)
        if cached is not None:
            return cached

        stale = soil_cache.get_stale(cache_key)
        unavailable: dict[str, str] = {}
        sources = self._safe_sources_by_type({"soil_data"}, unavailable_key="soil", unavailable=unavailable)
        soil = self._collect_soil_entry(farm=farm, location=location, sources=sources)
        if soil is None and stale is not None:
            return stale.model_copy(
                update={
                    "provider_health": self._collect_provider_health(),
                    "unavailable": self._merge_unavailable(stale.unavailable, unavailable or {"soil": "Using cached soil intelligence"}),
                    "generated_at": datetime.now(timezone.utc),
                }
            )
        response = SoilIntelligenceResponseRead(
            farm_id=farm.id,
            farm_name=farm.farm_name,
            crop=farm.crop,
            soil=soil,
            provider_health=self._collect_provider_health(),
            unavailable=unavailable if soil is None else {},
            generated_at=datetime.now(timezone.utc),
        )
        soil_cache.set(cache_key, response)
        return response

    def get_risk_intelligence(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        farm: Farm | None = None,
        weather: WeatherIntelligenceRead | None = None,
        advisories: AdvisoryIntelligenceResponseRead | None = None,
        news: NewsIntelligenceResponseRead | None = None,
    ) -> FarmRiskRead:
        farm = farm or self._get_farm(user_id=user_id, farm_id=farm_id)
        weather = weather or self._safe_weather_intelligence(user_id=user_id, farm_id=farm_id, farm=farm)
        advisories = advisories or self.get_advisory_intelligence(user_id=user_id, farm_id=farm_id, farm=farm)
        news = news or self.get_news_intelligence(user_id=user_id, farm_id=farm_id, farm=farm)
        cache_key = f"{farm.id}"
        cached = risk_cache.get(cache_key)
        if cached is not None:
            return cached

        unavailable: dict[str, str] = {}
        risk_sources = self._safe_sources_by_type(
            ALERT_SOURCE_TYPES,
            unavailable_key="risk",
            unavailable=unavailable,
        )
        pest_alerts, disease_alerts = self._collect_risk_alerts(farm=farm, sources=risk_sources)
        risk_score = self._compute_risk_score(
            weather=weather,
            advisories=advisories.government_advisories,
            news_items=news.news,
            pest_alerts=pest_alerts,
            disease_alerts=disease_alerts,
        )
        if not pest_alerts and not disease_alerts and unavailable:
            stale = risk_cache.get_stale(cache_key)
            if stale is not None:
                return stale.model_copy(
                    update={
                        "provider_health": self._collect_provider_health(),
                        "unavailable": self._merge_unavailable(stale.unavailable, unavailable),
                        "generated_at": datetime.now(timezone.utc),
                    }
                )
        response = FarmRiskRead(
            farm_id=farm.id,
            farm_name=farm.farm_name,
            crop=farm.crop,
            risk_score=risk_score,
            pest_alerts=pest_alerts,
            disease_alerts=disease_alerts,
            provider_health=self._collect_provider_health(),
            unavailable=unavailable,
            generated_at=datetime.now(timezone.utc),
        )
        risk_cache.set(cache_key, response)
        return response

    def get_farm_weather_response(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> FarmWeatherRead:
        farm = self._get_farm(user_id=user_id, farm_id=farm_id)
        weather = self.get_weather_intelligence(user_id=user_id, farm_id=farm_id, farm=farm)
        if weather.weather is None or weather.resolved_location is None:
            raise WeatherProviderError(
                weather.unavailable.get("weather") or "Weather data is unavailable",
            )
        advice = self._build_advice(
            farm=farm,
            current=weather.weather,
            forecast=weather.forecast,
        )
        return FarmWeatherRead(
            farm_id=farm.id,
            farm_name=farm.farm_name,
            crop=farm.crop,
            resolved_location=weather.resolved_location,
            current=weather.weather,
            forecast=weather.forecast,
            advice=advice,
            source="; ".join(
                sorted(
                    {
                        health.provider
                        for health in weather.provider_health
                        if health.provider_type == "weather" and health.status == "healthy"
                    }
                )
            )
            or "weather",
            fetched_at=weather.generated_at,
        )

    def build_ai_context(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> tuple[dict[str, Any], str]:
        intelligence = self.get_farm_intelligence(user_id=user_id, farm_id=farm_id)
        snapshot = intelligence.model_dump(mode="json")
        lines = [
            "External agricultural intelligence:",
            f"- Risk score: {intelligence.risk_score:.1f}/100",
        ]
        if intelligence.weather is not None:
            lines.append(
                f"- Weather: {intelligence.weather.condition}; temperature {intelligence.weather.temperature_c} C; humidity {intelligence.weather.relative_humidity_percent}%",
            )
        if intelligence.soil is not None:
            lines.append(
                f"- Soil: type {intelligence.soil.soil_type or 'unknown'}; pH {intelligence.soil.ph}; texture {intelligence.soil.texture or 'unknown'}",
            )
        if intelligence.market:
            top_market = intelligence.market[0]
            lines.append(
                f"- Market: {top_market.market} price {top_market.price} for {top_market.crop}; trend {top_market.trend or 'unknown'}",
            )
        if intelligence.government_advisories:
            lines.append(
                f"- Government advisory: {intelligence.government_advisories[0].title}",
            )
        if intelligence.pest_alerts:
            lines.append(f"- Pest alert: {intelligence.pest_alerts[0].title}")
        if intelligence.disease_alerts:
            lines.append(f"- Disease alert: {intelligence.disease_alerts[0].title}")
        if intelligence.unavailable:
            for key, value in intelligence.unavailable.items():
                lines.append(f"- {key} unavailable: {value}")
        return snapshot, "\n".join(lines)

    def _safe_weather_intelligence(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        farm: Farm,
    ) -> WeatherIntelligenceRead:
        try:
            return self.get_weather_intelligence(
                user_id=user_id,
                farm_id=farm_id,
                farm=farm,
            )
        except (WeatherLocationNotFoundError, WeatherProviderError, WeatherResponseParseError) as exc:
            logger.warning(
                "Weather intelligence unavailable: farm_id=%s error=%s",
                farm_id,
                str(exc),
            )
            return WeatherIntelligenceRead(
                farm_id=farm.id,
                farm_name=farm.farm_name,
                crop=farm.crop,
                resolved_location=None,
                weather=None,
                forecast=[],
                provider_health=self._collect_provider_health(),
                unavailable={"weather": str(exc)},
                generated_at=datetime.now(timezone.utc),
            )

    def _get_farm(self, *, user_id: uuid.UUID, farm_id: uuid.UUID) -> Farm:
        try:
            return self.farm_service.get_farm(user_id, farm_id)
        except FarmNotFoundError:
            raise
        except FarmPersistenceError:
            raise
        except SQLAlchemyError as exc:
            raise FarmPersistenceError from exc

    def _get_sources_by_type(self, source_types: set[str]) -> list[IntelligenceSource]:
        try:
            return list(self.repository.list_active_sources_for_types(source_types))
        except SQLAlchemyError as exc:
            raise IntelligencePersistenceError from exc

    def _safe_sources_by_type(
        self,
        source_types: set[str],
        *,
        unavailable_key: str,
        unavailable: dict[str, str],
    ) -> list[IntelligenceSource]:
        try:
            return self._get_sources_by_type(source_types)
        except IntelligencePersistenceError as exc:
            unavailable[unavailable_key] = str(exc)
            return []

    def _collect_market_entries(
        self,
        *,
        farm: Farm,
        sources: list[IntelligenceSource],
    ) -> list[MarketIntelligenceRead]:
        results: list[MarketIntelligenceRead] = []
        seen: set[tuple[str, str, str | None]] = set()
        for source in sources:
            try:
                payload = self._fetch_source_payload(source, farm=farm, location=None)
                for item in self._extract_items(payload, source):
                    crop = str(self._mapped_value(item, source, "crop", ["crop", "commodity"]) or farm.crop).strip()
                    if crop.lower() != farm.crop.lower():
                        continue
                    market_name = str(self._mapped_value(item, source, "market", ["market", "mandi"]) or "").strip()
                    if not market_name:
                        continue
                    district = self._optional_string(self._mapped_value(item, source, "district", ["district"]))
                    state = self._optional_string(self._mapped_value(item, source, "state", ["state"]))
                    key = (source.name, market_name, district)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append(
                        MarketIntelligenceRead(
                            source_name=source.name,
                            crop=crop,
                            market=market_name,
                            district=district,
                            state=state,
                            price=_optional_float(self._mapped_value(item, source, "price", ["price", "modal_price"])),
                            arrivals=_optional_float(self._mapped_value(item, source, "arrivals", ["arrivals", "arrival_quantity"])),
                            trend=self._optional_string(self._mapped_value(item, source, "trend", ["trend"])),
                            unit=self._optional_string(self._mapped_value(item, source, "unit", ["unit"])),
                            observed_at=_parse_datetime(self._mapped_value(item, source, "observed_at", ["observed_at", "date"])),
                            metadata={"source_url": source.url},
                        )
                    )
            except IntelligenceSourceError as exc:
                logger.warning(
                    "Market provider failed: source_id=%s source_name=%s error=%s",
                    source.id,
                    source.name,
                    str(exc),
                )
        results.sort(key=lambda item: (item.district != farm.district, item.market.lower()))
        return results[:12]

    def _collect_soil_entry(
        self,
        *,
        farm: Farm,
        location: WeatherLocationRead | None,
        sources: list[IntelligenceSource],
    ) -> SoilIntelligenceRead | None:
        for source in sources:
            try:
                payload = self._fetch_source_payload(source, farm=farm, location=location)
                item = self._extract_single_item(payload, source)
                if item is None:
                    continue
                nutrient_estimates = self._mapped_dict(
                    item,
                    source,
                    "nutrients",
                    default_keys=["nutrients", "nutrient_estimates"],
                )
                soil = SoilIntelligenceRead(
                    source_name=source.name,
                    soil_type=self._optional_string(self._mapped_value(item, source, "soil_type", ["soil_type", "classification"])) or farm.soil_type,
                    ph=_optional_float(self._mapped_value(item, source, "ph", ["ph", "pH"])),
                    organic_carbon=_optional_float(self._mapped_value(item, source, "organic_carbon", ["organic_carbon", "soc"])),
                    nutrient_estimates=nutrient_estimates,
                    texture=self._optional_string(self._mapped_value(item, source, "texture", ["texture"])),
                    observed_at=_parse_datetime(self._mapped_value(item, source, "observed_at", ["observed_at", "date"])),
                    metadata={"source_url": source.url},
                )
                return soil
            except IntelligenceSourceError as exc:
                logger.warning(
                    "Soil provider failed: source_id=%s source_name=%s error=%s",
                    source.id,
                    source.name,
                    str(exc),
                )
        return None

    def _collect_risk_alerts(
        self,
        *,
        farm: Farm,
        sources: list[IntelligenceSource],
    ) -> tuple[list[RiskAlertRead], list[RiskAlertRead]]:
        alerts: list[RiskAlertRead] = []
        for source in sources:
            try:
                payload = self._fetch_source_payload(source, farm=farm, location=None)
                for item in self._extract_items(payload, source):
                    title = str(self._mapped_value(item, source, "title", ["title", "headline"]) or "").strip()
                    if not title:
                        continue
                    alert_type = self._optional_string(self._mapped_value(item, source, "alert_type", ["alert_type", "type"])) or source.source_type
                    districts = self._string_list(self._mapped_value(item, source, "affected_districts", ["affected_districts", "districts"]))
                    if districts and farm.district.lower() not in {district.lower() for district in districts} and farm.state.lower() not in {district.lower() for district in districts}:
                        continue
                    alerts.append(
                        RiskAlertRead(
                            source_name=source.name,
                            alert_type=alert_type,
                            title=title,
                            summary=self._optional_string(self._mapped_value(item, source, "summary", ["summary", "description"])),
                            severity=self._normalize_severity(self._optional_string(self._mapped_value(item, source, "severity", ["severity"]))),
                            affected_districts=districts,
                            recommended_actions=self._string_list(self._mapped_value(item, source, "recommended_actions", ["recommended_actions", "actions"])),
                            url=self._optional_string(self._mapped_value(item, source, "url", ["url", "link"])) or source.url,
                            published_at=_parse_datetime(self._mapped_value(item, source, "published_at", ["published_at", "date"])),
                            metadata={"source_url": source.url},
                        )
                    )
            except IntelligenceSourceError as exc:
                logger.warning(
                    "Risk provider failed: source_id=%s source_name=%s error=%s",
                    source.id,
                    source.name,
                    str(exc),
                )

        archived_alerts = self._rank_archived_articles(
            farm=farm,
            article_types=ALERT_SOURCE_TYPES,
            limit=10,
        )
        for article in archived_alerts:
            category = (article.category or "").lower()
            title_text = article.title.lower()
            alert_type = "disease_alert" if "disease" in category or "disease" in title_text else "pest_alert"
            alerts.append(
                RiskAlertRead(
                    source_name=article.source_name,
                    alert_type=alert_type,
                    title=article.title,
                    summary=article.summary,
                    severity=self._severity_from_text(article.summary or article.title),
                    affected_districts=article.district_tags or ([farm.district] if not article.district_tags else []),
                    recommended_actions=[],
                    url=article.url,
                    published_at=article.published_at,
                    metadata=article.article_metadata,
                )
            )

        pest_alerts = [item for item in alerts if "pest" in item.alert_type]
        disease_alerts = [item for item in alerts if "disease" in item.alert_type]
        pest_alerts.sort(key=lambda item: (self._severity_rank(item.severity), item.published_at or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        disease_alerts.sort(key=lambda item: (self._severity_rank(item.severity), item.published_at or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return pest_alerts[:8], disease_alerts[:8]

    def _rank_archived_articles(
        self,
        *,
        farm: Farm,
        article_types: set[str],
        limit: int,
    ) -> list[NewsArticle]:
        try:
            articles = list(self.repository.list_recent_for_farm_context(farm=farm, article_types=article_types, limit=max(limit * 3, 20)))
        except SQLAlchemyError as exc:
            raise IntelligencePersistenceError from exc
        ranked = sorted(
            articles,
            key=lambda article: self._article_relevance(article, farm),
            reverse=True,
        )
        return ranked[:limit]

    def _article_to_advisory(self, article: NewsArticle, farm: Farm) -> GovernmentAdvisoryRead:
        return GovernmentAdvisoryRead(
            source_name=article.source_name,
            title=article.title,
            summary=article.summary,
            category=article.category,
            url=article.url,
            published_at=article.published_at,
            crop_tags=article.crop_tags,
            state_tags=article.state_tags,
            district_tags=article.district_tags,
            relevance_score=self._article_relevance(article, farm),
            metadata=article.article_metadata,
        )

    def _article_to_news_item(self, article: NewsArticle, farm: Farm) -> FarmNewsItemRead:
        return FarmNewsItemRead(
            source_name=article.source_name,
            title=article.title,
            summary=article.summary,
            category=article.category,
            url=article.url,
            published_at=article.published_at,
            crop_tags=article.crop_tags,
            state_tags=article.state_tags,
            district_tags=article.district_tags,
            relevance_score=self._article_relevance(article, farm),
            metadata=article.article_metadata,
        )

    def _article_relevance(self, article: NewsArticle, farm: Farm) -> float:
        score = 0.0
        crop = farm.crop.lower()
        district = farm.district.lower()
        state = farm.state.lower()
        text = " ".join(
            part
            for part in [article.title, article.summary or "", article.content or "", article.category or ""]
            if part
        ).lower()
        if crop in {tag.lower() for tag in article.crop_tags} or crop in text:
            score += 4
        if district in {tag.lower() for tag in article.district_tags} or district in text:
            score += 5
        if state in {tag.lower() for tag in article.state_tags} or state in text:
            score += 3
        if article.published_at is not None:
            age_days = max((datetime.now(timezone.utc) - article.published_at).days, 0)
            score += max(0, 3 - min(age_days, 3))
        return score

    def _compute_risk_score(
        self,
        *,
        weather: WeatherIntelligenceRead,
        advisories: list[GovernmentAdvisoryRead],
        news_items: list[FarmNewsItemRead],
        pest_alerts: list[RiskAlertRead],
        disease_alerts: list[RiskAlertRead],
    ) -> float:
        score = 15.0
        if weather.weather is not None:
            if weather.weather.relative_humidity_percent is not None and weather.weather.relative_humidity_percent >= 85:
                score += 10
            if weather.weather.wind_gusts_kmh is not None and weather.weather.wind_gusts_kmh >= 35:
                score += 6
        for forecast_day in weather.forecast[:3]:
            if (forecast_day.precipitation_sum_mm or 0) >= 15:
                score += 5
            if (forecast_day.relative_humidity_mean_percent or 0) >= 85:
                score += 4
        score += min(len(advisories) * 3, 12)
        score += min(len(news_items) * 1.5, 9)
        score += sum(self._severity_rank(item.severity) * 5 for item in pest_alerts[:3])
        score += sum(self._severity_rank(item.severity) * 5 for item in disease_alerts[:3])
        return round(min(score, 100), 2)

    def _fetch_source_payload(
        self,
        source: IntelligenceSource,
        *,
        farm: Farm,
        location: WeatherLocationRead | None,
    ) -> Any:
        adapter = BaseProviderAdapter()
        adapter.provider_name = source.name
        adapter.provider_type = source.source_type
        url = self._expand_source_url(source.url, farm=farm, location=location)
        payload = adapter._fetch_json_any(url) if source.source_format.lower() == "json" else self._fetch_bytes(url, source)
        return payload

    def _fetch_bytes(self, url: str, source: IntelligenceSource) -> bytes:
        cache_key = f"source-bytes:{source.id}"
        last_error: Exception | None = None
        started = time.monotonic()
        for attempt in range(settings.intelligence_request_retries):
            try:
                request = Request(url, headers={"User-Agent": "ai-agronomist/0.1"})
                with urlopen(
                    request,
                    timeout=settings.intelligence_request_timeout_seconds,
                ) as response:
                    payload = response.read()
                latency_ms = int((time.monotonic() - started) * 1000)
                provider_health_cache.set(
                    cache_key,
                    ProviderHealthRead(
                        provider=source.name,
                        provider_type=source.source_type,
                        status="healthy",
                        checked_at=datetime.now(timezone.utc),
                        latency_ms=latency_ms,
                        consecutive_failures=0,
                    ),
                )
                logger.info(
                    "Provider health: provider=%s type=%s status=healthy latency_ms=%s url=%s",
                    source.name,
                    source.source_type,
                    latency_ms,
                    url,
                )
                return payload
            except (HTTPError, URLError, TimeoutError) as exc:
                last_error = exc
                backoff_seconds = min(2**attempt, 8)
                logger.warning(
                    "Provider request failed: provider=%s type=%s url=%s attempt=%s backoff_seconds=%s error=%s",
                    source.name,
                    source.source_type,
                    url,
                    attempt + 1,
                    backoff_seconds,
                    str(exc),
                )
                if attempt < settings.intelligence_request_retries - 1:
                    time.sleep(backoff_seconds)
        previous = provider_health_cache.get_stale(cache_key)
        provider_health_cache.set(
            cache_key,
            ProviderHealthRead(
                provider=source.name,
                provider_type=source.source_type,
                status="unhealthy",
                detail=str(last_error) if last_error else "request failed",
                checked_at=datetime.now(timezone.utc),
                latency_ms=int((time.monotonic() - started) * 1000),
                consecutive_failures=(previous.consecutive_failures if previous else 0) + 1,
            ),
        )
        raise IntelligenceSourceError(f"Unable to fetch source: {source.name}") from last_error

    def _expand_source_url(
        self,
        url: str,
        *,
        farm: Farm,
        location: WeatherLocationRead | None,
    ) -> str:
        data = {
            "farm_name": farm.farm_name,
            "crop": farm.crop,
            "location": farm.location,
            "village": farm.village,
            "district": farm.district,
            "state": farm.state,
            "soil_type": farm.soil_type or "",
            "latitude": location.latitude if location is not None else "",
            "longitude": location.longitude if location is not None else "",
        }
        try:
            return url.format(**data)
        except KeyError:
            return url

    def _extract_items(
        self,
        payload: Any,
        source: IntelligenceSource,
    ) -> list[dict[str, Any]]:
        source_format = source.source_format.lower()
        if source_format == "json":
            if isinstance(payload, list):
                items = payload
                return [item for item in items if isinstance(item, dict)]
            if not isinstance(payload, dict):
                raise IntelligenceSourceError("JSON source payload must be an object or list")
            items_path = str(source.source_metadata.get("items_path", "items"))
            items = self.intelligence_service._resolve_metadata_path(payload, items_path)  # type: ignore[attr-defined]
            if items is None:
                items = []
            if not isinstance(items, list):
                raise IntelligenceSourceError("JSON source items path must resolve to a list")
            return [item for item in items if isinstance(item, dict)]
        if source_format in {"xml", "rss", "atom"}:
            if not isinstance(payload, bytes):
                raise IntelligenceSourceError("XML payload must be bytes")
            parsed = self.intelligence_service._parse_source(source=source, payload=payload)  # type: ignore[attr-defined]
            return [self._parsed_article_to_dict(item) for item in parsed]
        raise IntelligenceSourceError(f"Unsupported source format for mapped intelligence: {source.source_format}")

    def _extract_single_item(
        self,
        payload: Any,
        source: IntelligenceSource,
    ) -> dict[str, Any] | None:
        if source.source_format.lower() == "json" and isinstance(payload, dict):
            item_path = str(source.source_metadata.get("item_path", ""))
            if item_path:
                item = self.intelligence_service._resolve_metadata_path(payload, item_path)  # type: ignore[attr-defined]
                if isinstance(item, dict):
                    return item
            return payload
        if source.source_format.lower() == "json" and isinstance(payload, list):
            return payload[0] if payload and isinstance(payload[0], dict) else None
        items = self._extract_items(payload, source)
        return items[0] if items else None

    def _mapped_value(
        self,
        item: dict[str, Any],
        source: IntelligenceSource,
        logical_key: str,
        default_keys: list[str],
    ) -> Any:
        field_map = source.source_metadata.get("field_map", {})
        mapped_path = field_map.get(logical_key) if isinstance(field_map, dict) else None
        if isinstance(mapped_path, str):
            resolved = self.intelligence_service._resolve_metadata_path(item, mapped_path)  # type: ignore[attr-defined]
            if resolved is not None:
                return resolved
        for key in default_keys:
            if key in item:
                return item.get(key)
        return None

    def _mapped_dict(
        self,
        item: dict[str, Any],
        source: IntelligenceSource,
        logical_key: str,
        *,
        default_keys: list[str],
    ) -> dict[str, float | str | None]:
        value = self._mapped_value(item, source, logical_key, default_keys)
        if isinstance(value, dict):
            normalized: dict[str, float | str | None] = {}
            for key, raw_value in value.items():
                if raw_value is None:
                    normalized[str(key)] = None
                    continue
                if isinstance(raw_value, (int, float)):
                    normalized[str(key)] = float(raw_value)
                else:
                    normalized[str(key)] = str(raw_value)
            return normalized
        return {}

    def _parsed_article_to_dict(self, article: ParsedArticle) -> dict[str, Any]:
        return {
            "title": article.title,
            "url": article.url,
            "summary": article.summary,
            "content": article.content,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            **article.metadata,
        }

    def _normalize_severity(self, value: str | None) -> str:
        text = (value or "").strip().lower()
        if text in {"critical", "severe", "high"}:
            return "high"
        if text in {"moderate", "medium"}:
            return "moderate"
        if text in {"low", "minor"}:
            return "low"
        return "moderate"

    def _severity_from_text(self, text: str) -> str:
        lowered = text.lower()
        if any(term in lowered for term in ["severe", "critical", "urgent", "outbreak"]):
            return "high"
        if any(term in lowered for term in ["moderate", "watch", "warning"]):
            return "moderate"
        return "low"

    def _severity_rank(self, severity: str) -> int:
        return {"low": 1, "moderate": 2, "high": 3}.get(severity.lower(), 1)

    def _collect_provider_health(self) -> list[ProviderHealthRead]:
        seen: dict[tuple[str, str], ProviderHealthRead] = {}
        for cache in [
            provider_health_cache,
        ]:
            entries = getattr(cache, "_entries", {})
            for entry in entries.values():
                value = entry.value
                if isinstance(value, ProviderHealthRead):
                    seen[(value.provider_type, value.provider)] = value
        return sorted(
            seen.values(),
            key=lambda item: (item.provider_type, item.provider),
        )

    def _merge_health(self, *health_lists: list[ProviderHealthRead]) -> list[ProviderHealthRead]:
        merged: dict[tuple[str, str], ProviderHealthRead] = {}
        for health_list in health_lists:
            for item in health_list:
                merged[(item.provider_type, item.provider)] = item
        return sorted(merged.values(), key=lambda item: (item.provider_type, item.provider))

    def _merge_unavailable(self, *unavailable_dicts: dict[str, str]) -> dict[str, str]:
        merged: dict[str, str] = {}
        for item in unavailable_dicts:
            merged.update(item)
        return merged

    def _optional_string(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [part.strip() for part in value.replace("|", ",").split(",") if part.strip()]
        return []

    def _build_advice(
        self,
        *,
        farm: Farm,
        current: CurrentWeatherRead,
        forecast: list[DailyWeatherRead],
    ) -> FarmWeatherAdviceRead:
        crop = farm.crop
        soil_type = (farm.soil_type or "").lower()
        irrigation_type = farm.irrigation_type or "your irrigation system"
        next_two_day_rain = self._sum_precipitation(forecast[:2])
        next_three_day_rain = self._sum_precipitation(forecast[:3])
        next_seven_day_rain = self._sum_precipitation(forecast)
        max_temp = self._max_value(day.temperature_max_c for day in forecast)
        max_apparent_temp = self._max_value(
            day.apparent_temperature_max_c for day in forecast
        )
        max_wind = self._max_value(day.wind_speed_max_kmh for day in forecast)
        max_gust = self._max_value(day.wind_gusts_max_kmh for day in forecast)
        max_rain_probability = self._max_value(
            day.precipitation_probability_max_percent for day in forecast[:2]
        )
        max_humidity = self._max_value(
            day.relative_humidity_mean_percent for day in forecast
        )
        return FarmWeatherAdviceRead(
            irrigation=self._irrigation_advice(
                crop=crop,
                irrigation_type=irrigation_type,
                soil_type=soil_type,
                next_two_day_rain=next_two_day_rain,
                next_three_day_rain=next_three_day_rain,
                max_temp=max_temp,
            ),
            rainfall=self._rainfall_advice(
                crop=crop,
                next_two_day_rain=next_two_day_rain,
                next_seven_day_rain=next_seven_day_rain,
            ),
            spraying=self._spraying_advice(
                max_wind=max_wind,
                max_gust=max_gust,
                max_rain_probability=max_rain_probability,
                next_two_day_rain=next_two_day_rain,
                max_humidity=max_humidity,
            ),
            heat=self._heat_advice(
                crop=crop,
                max_temp=max_temp,
                max_apparent_temp=max_apparent_temp,
            ),
            wind=self._wind_advice(max_wind=max_wind, max_gust=max_gust),
            humidity=self._humidity_advice(
                crop=crop,
                current_humidity=current.relative_humidity_percent,
                max_humidity=max_humidity,
            ),
        )

    def _irrigation_advice(
        self,
        *,
        crop: str,
        irrigation_type: str,
        soil_type: str,
        next_two_day_rain: float,
        next_three_day_rain: float,
        max_temp: float | None,
    ) -> list[str]:
        advice: list[str] = []
        if next_two_day_rain >= 20:
            advice.append(f"Pause routine irrigation for {crop}; significant rain is forecast soon.")
        elif next_three_day_rain >= 5:
            advice.append(f"Reduce irrigation for {crop} and recheck soil moisture after rainfall.")
        else:
            advice.append(f"Rainfall looks limited; plan {irrigation_type} based on field soil moisture.")
        if max_temp is not None and max_temp >= 35 and next_three_day_rain < 5:
            advice.append("Use early morning or evening irrigation windows to reduce heat stress.")
        if "sandy" in soil_type:
            advice.append("Sandy soil can dry quickly, so monitor moisture more often.")
        elif "clay" in soil_type:
            advice.append("Clay soil holds water longer; avoid waterlogging after rain.")
        return advice

    def _rainfall_advice(self, *, crop: str, next_two_day_rain: float, next_seven_day_rain: float) -> list[str]:
        if next_seven_day_rain >= 50:
            return [f"Heavy cumulative rainfall may affect {crop}; clear drainage channels and inspect low spots."]
        if next_two_day_rain >= 15:
            return ["Rain is likely soon; delay field operations that need dry soil."]
        if next_seven_day_rain < 5:
            return ["Very little rain is forecast; conserve soil moisture with mulch or shallow cultivation where appropriate."]
        return ["Rainfall looks moderate; use field checks before changing irrigation or fertilizer timing."]

    def _spraying_advice(
        self,
        *,
        max_wind: float | None,
        max_gust: float | None,
        max_rain_probability: float | None,
        next_two_day_rain: float,
        max_humidity: float | None,
    ) -> list[str]:
        advice: list[str] = []
        if self._is_at_least(max_gust, 35) or self._is_at_least(max_wind, 20):
            advice.append("Avoid spraying during windy periods because drift risk is high.")
        if next_two_day_rain >= 5 or self._is_at_least(max_rain_probability, 60):
            advice.append("Delay sprays if possible until leaves are dry and rain risk is lower.")
        if self._is_at_least(max_humidity, 85):
            advice.append("High humidity can increase disease pressure; scout before spraying and follow local extension guidance.")
        if not advice:
            advice.append("A calm, dry window may be suitable for spraying, but follow the product label and local guidance.")
        return advice

    def _heat_advice(self, *, crop: str, max_temp: float | None, max_apparent_temp: float | None) -> list[str]:
        heat_value = max_apparent_temp if max_apparent_temp is not None else max_temp
        if heat_value is None:
            return ["Temperature data is limited; monitor field stress directly."]
        if heat_value >= 40:
            return [
                f"Severe heat stress is possible for {crop}; avoid midday operations and protect seedlings.",
                "Provide shade and water access for livestock and workers during peak heat.",
            ]
        if heat_value >= 35:
            return [
                f"Heat stress risk is elevated for {crop}; check wilting in the afternoon.",
                "Schedule labor-intensive field work for cooler hours.",
            ]
        return ["Heat risk looks manageable, but keep monitoring young plants and nursery beds."]

    def _wind_advice(self, *, max_wind: float | None, max_gust: float | None) -> list[str]:
        if self._is_at_least(max_gust, 45):
            return [
                "Strong gusts are possible; secure nursery covers, trellises, shade nets, and loose equipment.",
                "Avoid spraying and risky equipment work during gusty periods.",
            ]
        if self._is_at_least(max_gust, 30) or self._is_at_least(max_wind, 20):
            return ["Moderate wind may affect spraying and young plants; choose calmer hours for field work."]
        return ["Wind risk looks low for routine farm operations."]

    def _humidity_advice(self, *, crop: str, current_humidity: int | None, max_humidity: float | None) -> list[str]:
        humidity_value = max_humidity if max_humidity is not None else (float(current_humidity) if current_humidity is not None else None)
        if humidity_value is None:
            return ["Humidity data is limited; use crop canopy conditions and leaf wetness as field checks."]
        if humidity_value >= 85:
            return [f"High humidity can favor fungal and bacterial disease in {crop}; scout the lower canopy and improve airflow where possible."]
        if humidity_value <= 30:
            return [f"Low humidity may increase water stress in {crop}; monitor soil moisture and young plants closely."]
        return ["Humidity is in a moderate range; continue normal disease scouting."]

    def _sum_precipitation(self, days: list[DailyWeatherRead]) -> float:
        return sum(day.precipitation_sum_mm or 0 for day in days)

    def _max_value(self, values: Any) -> float | None:
        numeric_values = [float(value) for value in values if value is not None]
        return max(numeric_values) if numeric_values else None

    def _is_at_least(self, value: float | None, threshold: float) -> bool:
        return value is not None and value >= threshold


def _build_current_from_open_meteo(payload: dict[str, Any]) -> CurrentWeatherRead:
    current = payload.get("current")
    if not isinstance(current, dict):
        raise WeatherResponseParseError("Open-Meteo response is missing current data")
    weather_code = _optional_int(current.get("weather_code"))
    return CurrentWeatherRead(
        time=str(current.get("time") or ""),
        temperature_c=_optional_float(current.get("temperature_2m")),
        apparent_temperature_c=_optional_float(current.get("apparent_temperature")),
        relative_humidity_percent=_optional_int(current.get("relative_humidity_2m")),
        precipitation_mm=_optional_float(current.get("precipitation")),
        rain_mm=_optional_float(current.get("rain")),
        weather_code=weather_code,
        condition=WEATHER_CODE_LABELS.get(weather_code or -1, f"Weather code {weather_code}" if weather_code is not None else "Unknown"),
        cloud_cover_percent=_optional_int(current.get("cloud_cover")),
        wind_speed_kmh=_optional_float(current.get("wind_speed_10m")),
        wind_direction_degrees=_optional_int(current.get("wind_direction_10m")),
        wind_gusts_kmh=_optional_float(current.get("wind_gusts_10m")),
    )


def _build_forecast_from_open_meteo(payload: dict[str, Any]) -> list[DailyWeatherRead]:
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise WeatherResponseParseError("Open-Meteo response is missing daily data")
    dates = daily.get("time")
    if not isinstance(dates, list) or not dates:
        raise WeatherResponseParseError("Open-Meteo response contains no forecast days")
    forecast: list[DailyWeatherRead] = []
    for index, date_value in enumerate(dates[:7]):
        try:
            forecast_date = date.fromisoformat(str(date_value))
        except ValueError as exc:
            raise WeatherResponseParseError("Open-Meteo response contains an invalid forecast date") from exc
        weather_code = _optional_int(_indexed_value(daily, "weather_code", index))
        forecast.append(
            DailyWeatherRead(
                date=forecast_date,
                weather_code=weather_code,
                condition=WEATHER_CODE_LABELS.get(weather_code or -1, f"Weather code {weather_code}" if weather_code is not None else "Unknown"),
                temperature_max_c=_optional_float(_indexed_value(daily, "temperature_2m_max", index)),
                temperature_min_c=_optional_float(_indexed_value(daily, "temperature_2m_min", index)),
                apparent_temperature_max_c=_optional_float(_indexed_value(daily, "apparent_temperature_max", index)),
                apparent_temperature_min_c=_optional_float(_indexed_value(daily, "apparent_temperature_min", index)),
                precipitation_sum_mm=_optional_float(_indexed_value(daily, "precipitation_sum", index)),
                precipitation_probability_max_percent=_optional_int(_indexed_value(daily, "precipitation_probability_max", index)),
                relative_humidity_mean_percent=_optional_int(_indexed_value(daily, "relative_humidity_2m_mean", index)),
                wind_speed_max_kmh=_optional_float(_indexed_value(daily, "wind_speed_10m_max", index)),
                wind_gusts_max_kmh=_optional_float(_indexed_value(daily, "wind_gusts_10m_max", index)),
            )
        )
    return forecast


def _nested_value(payload: Any, *keys: str) -> Any:
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first_list_item(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise WeatherResponseParseError("Provider response contains invalid numeric data") from exc


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError) as exc:
        raise WeatherResponseParseError("Provider response contains invalid numeric data") from exc


def _indexed_value(data: dict[str, Any], key: str, index: int) -> Any:
    value = data.get(key)
    if not isinstance(value, list) or index >= len(value):
        return None
    return value[index]


def _meters_per_second_to_kmh(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value * 3.6, 3)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        except (TypeError, ValueError):
            return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
