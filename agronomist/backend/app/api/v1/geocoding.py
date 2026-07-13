from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_farmer, get_reverse_geocoding_service
from app.models.user import User
from app.schemas.geocoding import ReverseGeocodeRead
from app.services.geocoding_service import GeocodingProviderError, ReverseGeocodingService


router = APIRouter(prefix="/geocoding", tags=["geocoding"])


@router.get("/reverse", response_model=ReverseGeocodeRead)
def reverse_geocode(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    current_user: User = Depends(get_current_farmer),
    geocoding_service: ReverseGeocodingService = Depends(get_reverse_geocoding_service),
) -> ReverseGeocodeRead:
    del current_user
    try:
        return geocoding_service.reverse(latitude, longitude)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except GeocodingProviderError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reverse geocoding is temporarily unavailable",
        )
