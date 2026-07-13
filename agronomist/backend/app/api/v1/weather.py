from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_farmer, get_weather_service
from app.models.user import User
from app.schemas.weather import FarmWeatherRead
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    TimelinePersistenceError,
    WeatherLocationNotFoundError,
    WeatherProviderError,
    WeatherResponseParseError,
)
from app.services.weather_service import WeatherService


router = APIRouter(prefix="/farms/{farm_id}/weather", tags=["weather"])


@router.get("", response_model=FarmWeatherRead)
def get_farm_weather(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    weather_service: WeatherService = Depends(get_weather_service),
) -> FarmWeatherRead:
    try:
        return weather_service.get_farm_weather(
            user_id=current_user.id,
            farm_id=farm_id,
        )
    except FarmNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )
    except WeatherLocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except WeatherResponseParseError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Weather temporarily unavailable",
        )
    except WeatherProviderError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Weather temporarily unavailable",
        )
    except TimelinePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to log weather check",
        )
    except FarmPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch farm weather",
        )
