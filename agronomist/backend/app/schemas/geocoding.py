from __future__ import annotations

from pydantic import BaseModel


class ReverseGeocodeRead(BaseModel):
    latitude: float
    longitude: float
    formatted_address: str | None = None
    locality: str | None = None
    district: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    provider: str
    cache_hit: bool = False
