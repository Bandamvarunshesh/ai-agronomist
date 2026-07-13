from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_LAND_SIZE_ACRES = Decimal("99999999.99")
LOCATION_SOURCES = {"current_location", "map_selection", "manual"}


def validate_land_size_acres(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return value
    if value > MAX_LAND_SIZE_ACRES:
        raise ValueError("land_size_acres is too large")
    if value.as_tuple().exponent < -2:
        raise ValueError("land_size_acres cannot have more than 2 decimal places")
    return value


def validate_latitude(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return value
    if value < Decimal("-90") or value > Decimal("90"):
        raise ValueError("latitude must be between -90 and 90")
    return value


def validate_longitude(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return value
    if value < Decimal("-180") or value > Decimal("180"):
        raise ValueError("longitude must be between -180 and 180")
    return value


class FarmBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    farm_name: str = Field(min_length=1, max_length=255)
    crop: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=255)
    village: str = Field(min_length=1, max_length=100)
    locality: Optional[str] = Field(default=None, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    formatted_address: Optional[str] = Field(default=None, max_length=500)
    country: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    location_source: str = Field(default="manual", max_length=32)
    soil_type: Optional[str] = Field(default=None, max_length=100)
    land_size_acres: Decimal = Field(gt=0)
    irrigation_type: Optional[str] = Field(default=None, max_length=100)
    sowing_date: Optional[date] = None

    @field_validator(
        "soil_type",
        "irrigation_type",
        "formatted_address",
        "locality",
        "country",
        "postal_code",
    )
    @classmethod
    def empty_optional_strings_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value == "":
            return None
        return value

    @field_validator("land_size_acres")
    @classmethod
    def validate_land_size(cls, value: Decimal) -> Decimal:
        checked_value = validate_land_size_acres(value)
        if checked_value is None:
            raise ValueError("land_size_acres is required")
        return checked_value

    @field_validator("latitude")
    @classmethod
    def validate_latitude_value(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        return validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_longitude_value(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        return validate_longitude(value)

    @field_validator("location_source")
    @classmethod
    def validate_location_source(cls, value: str) -> str:
        if value not in LOCATION_SOURCES:
            raise ValueError("location_source is invalid")
        return value


class FarmCreate(FarmBase):
    pass


class FarmUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    farm_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    crop: Optional[str] = Field(default=None, min_length=1, max_length=100)
    location: Optional[str] = Field(default=None, min_length=1, max_length=255)
    village: Optional[str] = Field(default=None, min_length=1, max_length=100)
    locality: Optional[str] = Field(default=None, max_length=100)
    district: Optional[str] = Field(default=None, min_length=1, max_length=100)
    state: Optional[str] = Field(default=None, min_length=1, max_length=100)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    formatted_address: Optional[str] = Field(default=None, max_length=500)
    country: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    location_source: Optional[str] = Field(default=None, max_length=32)
    soil_type: Optional[str] = Field(default=None, max_length=100)
    land_size_acres: Optional[Decimal] = Field(default=None, gt=0)
    irrigation_type: Optional[str] = Field(default=None, max_length=100)
    sowing_date: Optional[date] = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        if not data:
            raise ValueError("At least one farm field must be provided")

        required_fields = {
            "farm_name",
            "crop",
            "location",
            "village",
            "district",
            "state",
            "land_size_acres",
        }
        null_fields = sorted(
            field for field in required_fields if field in data and data[field] is None
        )
        if null_fields:
            joined_fields = ", ".join(null_fields)
            raise ValueError(f"{joined_fields} cannot be null")

        return data

    @field_validator(
        "soil_type",
        "irrigation_type",
        "formatted_address",
        "locality",
        "country",
        "postal_code",
    )
    @classmethod
    def empty_optional_strings_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value == "":
            return None
        return value

    @field_validator("land_size_acres")
    @classmethod
    def validate_land_size(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        return validate_land_size_acres(value)

    @field_validator("latitude")
    @classmethod
    def validate_latitude_value(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        return validate_latitude(value)

    @field_validator("longitude")
    @classmethod
    def validate_longitude_value(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        return validate_longitude(value)

    @field_validator("location_source")
    @classmethod
    def validate_location_source(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in LOCATION_SOURCES:
            raise ValueError("location_source is invalid")
        return value


class FarmRead(FarmBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
