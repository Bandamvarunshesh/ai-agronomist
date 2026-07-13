from __future__ import annotations

import json
import threading
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.schemas.geocoding import ReverseGeocodeRead
from app.services.cache_service import TTLCache


class GeocodingProviderError(Exception):
    pass


geocoding_cache: TTLCache[ReverseGeocodeRead] = TTLCache(
    settings.geocoding_cache_ttl_seconds,
)
geocoding_rate_lock = threading.Lock()
last_geocoding_request_at = 0.0


class ReverseGeocodingAdapter:
    provider_name = "provider"

    def reverse(self, latitude: float, longitude: float) -> ReverseGeocodeRead:
        raise NotImplementedError


class NominatimReverseGeocodingAdapter(ReverseGeocodingAdapter):
    provider_name = "nominatim"

    def reverse(self, latitude: float, longitude: float) -> ReverseGeocodeRead:
        self._rate_limit()
        query = urlencode(
            {
                "format": "jsonv2",
                "lat": f"{latitude:.6f}",
                "lon": f"{longitude:.6f}",
                "addressdetails": 1,
            }
        )
        request = Request(
            f"{settings.nominatim_reverse_url}?{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": settings.nominatim_user_agent,
            },
        )

        try:
            with urlopen(request, timeout=settings.intelligence_request_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise GeocodingProviderError("Reverse geocoding is temporarily unavailable") from exc

        if not isinstance(payload, dict):
            raise GeocodingProviderError("Reverse geocoding returned invalid data")

        address = payload.get("address") if isinstance(payload.get("address"), dict) else {}
        return ReverseGeocodeRead(
            latitude=latitude,
            longitude=longitude,
            formatted_address=self._optional_string(payload.get("display_name")),
            locality=self._first_string(
                address,
                "village",
                "hamlet",
                "town",
                "city",
                "suburb",
                "neighbourhood",
            ),
            district=self._first_string(address, "county", "state_district", "district"),
            state=self._first_string(address, "state"),
            country=self._first_string(address, "country"),
            postal_code=self._first_string(address, "postcode"),
            provider=self.provider_name,
            cache_hit=False,
        )

    def _rate_limit(self) -> None:
        global last_geocoding_request_at
        min_interval_seconds = max(settings.geocoding_min_interval_ms, 0) / 1000
        with geocoding_rate_lock:
            now = time.monotonic()
            wait_seconds = min_interval_seconds - (now - last_geocoding_request_at)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            last_geocoding_request_at = time.monotonic()

    def _first_string(self, source: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = self._optional_string(source.get(key))
            if value:
                return value
        return None

    def _optional_string(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ReverseGeocodingService:
    def __init__(self) -> None:
        self.adapter = self._build_adapter()

    def reverse(self, latitude: float, longitude: float) -> ReverseGeocodeRead:
        if latitude < -90 or latitude > 90:
            raise ValueError("latitude must be between -90 and 90")
        if longitude < -180 or longitude > 180:
            raise ValueError("longitude must be between -180 and 180")

        cache_key = f"{self.adapter.provider_name}:{round(latitude, 5)}:{round(longitude, 5)}"
        cached = geocoding_cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(update={"cache_hit": True})

        result = self.adapter.reverse(latitude, longitude)
        geocoding_cache.set(cache_key, result)
        return result

    def _build_adapter(self) -> ReverseGeocodingAdapter:
        provider = settings.geocoding_provider.strip().lower()
        if provider == "nominatim":
            return NominatimReverseGeocodingAdapter()
        raise GeocodingProviderError("Reverse geocoding provider is not configured")
