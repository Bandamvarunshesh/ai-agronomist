from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.farm import Farm
from app.schemas.weather import (
    CurrentWeatherRead,
    DailyWeatherRead,
    FarmWeatherAdviceRead,
    FarmWeatherRead,
    WeatherLocationRead,
)
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    NotificationPersistenceError,
    TimelinePersistenceError,
    WeatherLocationNotFoundError,
    WeatherProviderError,
    WeatherResponseParseError,
)
from app.services.farm_service import FarmService
from app.services.notification_generation_service import NotificationGenerationService
from app.services.timeline_service import TimelineService


logger = logging.getLogger(__name__)

OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TIMEOUT_SECONDS = 10

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


class WeatherService:
    def __init__(self, db: Session):
        self.db = db
        self.farm_service = FarmService(db)
        self.notification_generation_service = NotificationGenerationService(db)
        self.timeline_service = TimelineService(db)

    def get_farm_weather(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        log_timeline: bool = True,
    ) -> FarmWeatherRead:
        farm = self._get_farm(user_id=user_id, farm_id=farm_id)
        location = self._resolve_location(farm)
        payload = self._fetch_forecast(location)
        current = self._build_current(payload)
        forecast = self._build_forecast(payload)
        advice = self._build_advice(farm=farm, current=current, forecast=forecast)

        weather = FarmWeatherRead(
            farm_id=farm.id,
            farm_name=farm.farm_name,
            crop=farm.crop,
            resolved_location=location,
            current=current,
            forecast=forecast,
            advice=advice,
            source="Open-Meteo",
            fetched_at=datetime.now(timezone.utc),
        )
        if log_timeline:
            try:
                self.timeline_service.add_event(
                    farm_id=farm.id,
                    user_id=user_id,
                    event_type="weather_check",
                    title="Weather checked",
                    description=f"{current.condition} for {farm.farm_name}",
                    source="weather",
                    payload={
                        "source": weather.source,
                        "resolved_location": location.model_dump(),
                        "current_condition": current.condition,
                        "temperature_c": current.temperature_c,
                        "forecast_days": len(forecast),
                    },
                )
                self.notification_generation_service.add_for_weather(
                    user_id=user_id,
                    farm=farm,
                    weather=weather,
                )
                self.db.commit()
            except (SQLAlchemyError, NotificationPersistenceError) as exc:
                self.db.rollback()
                raise TimelinePersistenceError from exc
        return weather

    def _get_farm(self, *, user_id: uuid.UUID, farm_id: uuid.UUID) -> Farm:
        try:
            return self.farm_service.get_farm(user_id, farm_id)
        except FarmNotFoundError:
            raise
        except FarmPersistenceError:
            raise
        except SQLAlchemyError as exc:
            raise FarmPersistenceError from exc

    def _resolve_location(self, farm: Farm) -> WeatherLocationRead:
        for query in self._build_location_queries(farm):
            payload = self._get_json(
                OPEN_METEO_GEOCODING_URL,
                {
                    "name": query,
                    "count": 1,
                    "language": "en",
                    "format": "json",
                },
            )
            result = self._first_geocoding_result(payload)
            if result is not None:
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

    def _first_geocoding_result(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        results = payload.get("results")
        if not isinstance(results, list) or not results:
            return None

        result = results[0]
        if not isinstance(result, dict):
            return None
        if "latitude" not in result or "longitude" not in result:
            return None
        return result

    def _fetch_forecast(self, location: WeatherLocationRead) -> dict[str, Any]:
        return self._get_json(
            OPEN_METEO_FORECAST_URL,
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "current": ",".join(CURRENT_VARIABLES),
                "daily": ",".join(DAILY_VARIABLES),
                "forecast_days": 7,
                "timezone": location.timezone or "auto",
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
            },
        )

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        full_url = f"{url}?{urlencode(params)}"
        request = Request(full_url, headers={"User-Agent": "ai-agronomist/0.1"})

        try:
            with urlopen(request, timeout=WEATHER_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            self._raise_provider_error(exc, url)
        except (URLError, TimeoutError) as exc:
            logger.exception("Open-Meteo request failed: url=%s error=%s", url, str(exc))
            raise WeatherProviderError("Open-Meteo weather request failed") from exc
        except json.JSONDecodeError as exc:
            logger.exception("Open-Meteo returned invalid JSON: url=%s", url)
            raise WeatherResponseParseError("Open-Meteo returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise WeatherResponseParseError("Open-Meteo JSON response must be an object")
        if payload.get("error"):
            reason = str(payload.get("reason") or "Open-Meteo returned an error")
            raise WeatherProviderError(reason)
        return payload

    def _raise_provider_error(self, exc: HTTPError, url: str) -> None:
        try:
            response_text = exc.read().decode("utf-8")
        except Exception:
            response_text = ""

        logger.exception(
            "Open-Meteo HTTP error: url=%s status_code=%s response=%s",
            url,
            exc.code,
            response_text,
        )
        raise WeatherProviderError("Open-Meteo weather request failed") from exc

    def _build_current(self, payload: dict[str, Any]) -> CurrentWeatherRead:
        current = payload.get("current")
        if not isinstance(current, dict):
            raise WeatherResponseParseError("Open-Meteo response is missing current data")

        weather_code = self._optional_int(current.get("weather_code"))
        return CurrentWeatherRead(
            time=str(current.get("time") or ""),
            temperature_c=self._optional_float(current.get("temperature_2m")),
            apparent_temperature_c=self._optional_float(
                current.get("apparent_temperature"),
            ),
            relative_humidity_percent=self._optional_int(
                current.get("relative_humidity_2m"),
            ),
            precipitation_mm=self._optional_float(current.get("precipitation")),
            rain_mm=self._optional_float(current.get("rain")),
            weather_code=weather_code,
            condition=self._weather_condition(weather_code),
            cloud_cover_percent=self._optional_int(current.get("cloud_cover")),
            wind_speed_kmh=self._optional_float(current.get("wind_speed_10m")),
            wind_direction_degrees=self._optional_int(
                current.get("wind_direction_10m"),
            ),
            wind_gusts_kmh=self._optional_float(current.get("wind_gusts_10m")),
        )

    def _build_forecast(self, payload: dict[str, Any]) -> list[DailyWeatherRead]:
        daily = payload.get("daily")
        if not isinstance(daily, dict):
            raise WeatherResponseParseError("Open-Meteo response is missing daily data")

        dates = self._list_value(daily, "time")
        forecast: list[DailyWeatherRead] = []
        for index, date_value in enumerate(dates[:7]):
            weather_code = self._optional_int(
                self._indexed_value(daily, "weather_code", index),
            )
            try:
                forecast_date = date.fromisoformat(str(date_value))
            except ValueError as exc:
                raise WeatherResponseParseError(
                    "Open-Meteo response contains an invalid forecast date",
                ) from exc

            forecast.append(
                DailyWeatherRead(
                    date=forecast_date,
                    weather_code=weather_code,
                    condition=self._weather_condition(weather_code),
                    temperature_max_c=self._optional_float(
                        self._indexed_value(daily, "temperature_2m_max", index),
                    ),
                    temperature_min_c=self._optional_float(
                        self._indexed_value(daily, "temperature_2m_min", index),
                    ),
                    apparent_temperature_max_c=self._optional_float(
                        self._indexed_value(daily, "apparent_temperature_max", index),
                    ),
                    apparent_temperature_min_c=self._optional_float(
                        self._indexed_value(daily, "apparent_temperature_min", index),
                    ),
                    precipitation_sum_mm=self._optional_float(
                        self._indexed_value(daily, "precipitation_sum", index),
                    ),
                    precipitation_probability_max_percent=self._optional_int(
                        self._indexed_value(
                            daily,
                            "precipitation_probability_max",
                            index,
                        ),
                    ),
                    relative_humidity_mean_percent=self._optional_int(
                        self._indexed_value(daily, "relative_humidity_2m_mean", index),
                    ),
                    wind_speed_max_kmh=self._optional_float(
                        self._indexed_value(daily, "wind_speed_10m_max", index),
                    ),
                    wind_gusts_max_kmh=self._optional_float(
                        self._indexed_value(daily, "wind_gusts_10m_max", index),
                    ),
                )
            )

        if not forecast:
            raise WeatherResponseParseError("Open-Meteo response contains no forecast days")
        return forecast

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

        irrigation = self._irrigation_advice(
            crop=crop,
            irrigation_type=irrigation_type,
            soil_type=soil_type,
            next_two_day_rain=next_two_day_rain,
            next_three_day_rain=next_three_day_rain,
            max_temp=max_temp,
        )
        rainfall = self._rainfall_advice(
            crop=crop,
            next_two_day_rain=next_two_day_rain,
            next_seven_day_rain=next_seven_day_rain,
        )
        spraying = self._spraying_advice(
            max_wind=max_wind,
            max_gust=max_gust,
            max_rain_probability=max_rain_probability,
            next_two_day_rain=next_two_day_rain,
            max_humidity=max_humidity,
        )
        heat = self._heat_advice(
            crop=crop,
            max_temp=max_temp,
            max_apparent_temp=max_apparent_temp,
        )
        wind = self._wind_advice(max_wind=max_wind, max_gust=max_gust)
        humidity = self._humidity_advice(
            crop=crop,
            current_humidity=current.relative_humidity_percent,
            max_humidity=max_humidity,
        )

        return FarmWeatherAdviceRead(
            irrigation=irrigation,
            rainfall=rainfall,
            spraying=spraying,
            heat=heat,
            wind=wind,
            humidity=humidity,
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
            advice.append(
                f"Pause routine irrigation for {crop}; significant rain is forecast soon.",
            )
        elif next_three_day_rain >= 5:
            advice.append(
                f"Reduce irrigation for {crop} and recheck soil moisture after rainfall.",
            )
        else:
            advice.append(
                f"Rainfall looks limited; plan {irrigation_type} based on field soil moisture.",
            )

        if max_temp is not None and max_temp >= 35 and next_three_day_rain < 5:
            advice.append(
                "Use early morning or evening irrigation windows to reduce heat stress.",
            )
        if "sandy" in soil_type:
            advice.append("Sandy soil can dry quickly, so monitor moisture more often.")
        elif "clay" in soil_type:
            advice.append("Clay soil holds water longer; avoid waterlogging after rain.")
        return advice

    def _rainfall_advice(
        self,
        *,
        crop: str,
        next_two_day_rain: float,
        next_seven_day_rain: float,
    ) -> list[str]:
        advice: list[str] = []
        if next_seven_day_rain >= 50:
            advice.append(
                f"Heavy cumulative rainfall may affect {crop}; clear drainage channels and inspect low spots.",
            )
        elif next_two_day_rain >= 15:
            advice.append("Rain is likely soon; delay field operations that need dry soil.")
        elif next_seven_day_rain < 5:
            advice.append("Very little rain is forecast; conserve soil moisture with mulch or shallow cultivation where appropriate.")
        else:
            advice.append("Rainfall looks moderate; use field checks before changing irrigation or fertilizer timing.")
        return advice

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

    def _heat_advice(
        self,
        *,
        crop: str,
        max_temp: float | None,
        max_apparent_temp: float | None,
    ) -> list[str]:
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

    def _wind_advice(
        self,
        *,
        max_wind: float | None,
        max_gust: float | None,
    ) -> list[str]:
        if self._is_at_least(max_gust, 45):
            return [
                "Strong gusts are possible; secure nursery covers, trellises, shade nets, and loose equipment.",
                "Avoid spraying and risky equipment work during gusty periods.",
            ]
        if self._is_at_least(max_gust, 30) or self._is_at_least(max_wind, 20):
            return [
                "Moderate wind may affect spraying and young plants; choose calmer hours for field work.",
            ]
        return ["Wind risk looks low for routine farm operations."]

    def _humidity_advice(
        self,
        *,
        crop: str,
        current_humidity: int | None,
        max_humidity: float | None,
    ) -> list[str]:
        humidity_value = max_humidity
        if humidity_value is None and current_humidity is not None:
            humidity_value = float(current_humidity)

        if humidity_value is None:
            return ["Humidity data is limited; use crop canopy conditions and leaf wetness as field checks."]
        if humidity_value >= 85:
            return [
                f"High humidity can favor fungal and bacterial disease in {crop}; scout the lower canopy and improve airflow where possible.",
            ]
        if humidity_value <= 30:
            return [
                f"Low humidity may increase water stress in {crop}; monitor soil moisture and young plants closely.",
            ]
        return ["Humidity is in a moderate range; continue normal disease scouting."]

    def _sum_precipitation(self, days: list[DailyWeatherRead]) -> float:
        return sum(day.precipitation_sum_mm or 0 for day in days)

    def _max_value(self, values: Any) -> float | None:
        numeric_values = [float(value) for value in values if value is not None]
        if not numeric_values:
            return None
        return max(numeric_values)

    def _is_at_least(self, value: float | None, threshold: float) -> bool:
        return value is not None and value >= threshold

    def _weather_condition(self, code: int | None) -> str:
        if code is None:
            return "Unknown"
        return WEATHER_CODE_LABELS.get(code, f"Weather code {code}")

    def _list_value(self, data: dict[str, Any], key: str) -> list[Any]:
        value = data.get(key)
        if not isinstance(value, list):
            raise WeatherResponseParseError(
                f"Open-Meteo response is missing daily {key}",
            )
        return value

    def _indexed_value(self, data: dict[str, Any], key: str, index: int) -> Any:
        value = data.get(key)
        if not isinstance(value, list) or index >= len(value):
            return None
        return value[index]

    def _optional_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise WeatherResponseParseError(
                "Open-Meteo response contains invalid numeric data",
            ) from exc

    def _optional_int(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise WeatherResponseParseError(
                "Open-Meteo response contains invalid numeric data",
            ) from exc
