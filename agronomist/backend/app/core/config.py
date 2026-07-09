from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # App
    app_name: str = "AI Agronomist MVP"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql://agronomist:agronomist_dev@localhost:5432/agronomist"

    # Authentication
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"

    # File uploads
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

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())


settings = Settings()
