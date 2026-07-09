from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.config import dictConfig

from app.core.config import settings


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    formatter_name = "json" if settings.log_format == "json" else "plain"
    handlers = ["default"]
    if settings.log_access:
        handlers.append("access")

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                },
                "json": {
                    "()": "app.core.logging.JsonLogFormatter",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter_name,
                },
                "access": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter_name,
                },
            },
            "root": {
                "level": settings.log_level.upper(),
                "handlers": ["default"],
            },
            "loggers": {
                "uvicorn.error": {
                    "level": settings.log_level.upper(),
                    "handlers": ["default"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": settings.log_level.upper(),
                    "handlers": ["access"] if settings.log_access else [],
                    "propagate": False,
                },
            },
        }
    )
