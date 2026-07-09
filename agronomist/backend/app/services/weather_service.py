from __future__ import annotations

import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.schemas.weather import FarmWeatherRead
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    NotificationPersistenceError,
    TimelinePersistenceError,
    WeatherProviderError,
)
from app.services.farm_intelligence_service import FarmIntelligenceService
from app.services.notification_generation_service import NotificationGenerationService
from app.services.timeline_service import TimelineService


class WeatherService:
    def __init__(self, db: Session):
        self.db = db
        self.intelligence_service = FarmIntelligenceService(db)
        self.notification_generation_service = NotificationGenerationService(db)
        self.timeline_service = TimelineService(db)

    def get_farm_weather(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        log_timeline: bool = True,
    ) -> FarmWeatherRead:
        try:
            weather = self.intelligence_service.get_farm_weather_response(
                user_id=user_id,
                farm_id=farm_id,
            )
        except FarmNotFoundError:
            raise
        except FarmPersistenceError:
            raise
        except WeatherProviderError:
            raise

        if log_timeline:
            try:
                self.timeline_service.add_event(
                    farm_id=weather.farm_id,
                    user_id=user_id,
                    event_type="weather_check",
                    title="Weather checked",
                    description=f"{weather.current.condition} for {weather.farm_name}",
                    source="weather",
                    payload={
                        "source": weather.source,
                        "resolved_location": weather.resolved_location.model_dump(),
                        "current_condition": weather.current.condition,
                        "temperature_c": weather.current.temperature_c,
                        "forecast_days": len(weather.forecast),
                    },
                )
                farm = self.intelligence_service._get_farm(user_id=user_id, farm_id=farm_id)
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
