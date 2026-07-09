from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # App
    app_name: str = "AI Agronomist MVP"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql://agronomist:agronomist_dev@localhost:5432/agronomist"
    database_ssl_mode: str | None = None
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout_seconds: int = 30
    database_pool_recycle_seconds: int = 1800
    database_connect_timeout_seconds: int = 10

    # Authentication
    secret_key: str = "dev-insecure-secret-key-change-before-production"
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"

    # Runtime
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
    )
    log_level: str = "INFO"
    log_format: Literal["plain", "json"] = "plain"
    log_access: bool = True

    # File uploads
    storage_backend: Literal["local"] = "local"
    upload_dir: str = "uploads"
    max_image_upload_size_mb: int = 10

    # Vision AI
    gemini_api_key: str = ""
    vision_provider: str = "gemini"
    gemini_model: str = "gemini-3.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    gemini_request_timeout_seconds: int = 20

    # Knowledge platform
    knowledge_storage_dir: str = "knowledge_uploads"
    knowledge_chunk_size: int = 1200
    knowledge_chunk_overlap: int = 180
    knowledge_search_cache_ttl_seconds: int = 300

    # Agricultural intelligence
    intelligence_source_config_path: str = "config/intelligence_sources.example.json"
    intelligence_sync_enabled: bool = False
    intelligence_sync_interval_seconds: int = 86400
    intelligence_request_timeout_seconds: int = 15
    intelligence_request_retries: int = 3
    news_cache_ttl_seconds: int = 300
    farm_weather_cache_ttl_seconds: int = 900
    farm_market_cache_ttl_seconds: int = 900
    farm_advisory_cache_ttl_seconds: int = 1800
    farm_soil_cache_ttl_seconds: int = 43200
    farm_risk_cache_ttl_seconds: int = 1800
    farm_news_cache_ttl_seconds: int = 900

    # External provider configuration
    open_meteo_geocoding_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    openweather_geocoding_url: str = "https://api.openweathermap.org/geo/1.0/direct"
    openweather_forecast_url: str = "https://api.openweathermap.org/data/2.5/forecast"
    openweather_api_key: str = ""
    weatherapi_base_url: str = "https://api.weatherapi.com/v1"
    weatherapi_api_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    startup_validate_database: bool = True
    startup_validate_pgvector: bool = True
    startup_validate_storage: bool = True

    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ORIGINS JSON value must be a list")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in text.split(",") if item.strip()]
        raise ValueError("CORS_ORIGINS must be a comma-separated string or JSON list")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        database_url = value.strip()
        if not database_url:
            raise ValueError("DATABASE_URL must not be empty")
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url[len("postgres://") :]
        return database_url

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        secret_key = value.strip()
        if not secret_key:
            raise ValueError("SECRET_KEY must not be empty")
        return secret_key

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production":
            if self.debug:
                raise ValueError("DEBUG must be false in production")
            if self.secret_key == "dev-insecure-secret-key-change-before-production":
                raise ValueError("SECRET_KEY must be set to a secure production value")
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            if not self.cors_origins:
                raise ValueError("CORS_ORIGINS must include at least one frontend origin in production")
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS cannot contain '*' in production")
            if not self.gemini_api_key.strip():
                raise ValueError("GEMINI_API_KEY is required in production")
            if self.storage_backend != "local":
                raise ValueError("Only the local storage backend is currently supported")
        return self

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def sqlalchemy_database_url(self) -> str:
        return self._database_url_with_ssl()

    @property
    def sqlalchemy_connect_args(self) -> dict[str, Any]:
        return {
            "connect_timeout": self.database_connect_timeout_seconds,
        }

    def _database_url_with_ssl(self) -> str:
        parts = urlsplit(self.database_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        ssl_mode = self.database_ssl_mode or self._infer_database_ssl_mode(parts.hostname)
        if ssl_mode and "sslmode" not in query:
            query["sslmode"] = ssl_mode
        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(query),
                parts.fragment,
            )
        )

    def _infer_database_ssl_mode(self, hostname: str | None) -> str | None:
        host = (hostname or "").lower()
        if "supabase" in host:
            return "require"
        return None


settings = Settings()
