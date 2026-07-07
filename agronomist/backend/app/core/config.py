from pydantic_settings import BaseSettings


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

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
