from __future__ import annotations

import os
from typing import Any

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.services.storage_service import StorageService


def database_health() -> dict[str, Any]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "url": _redact_database_url(settings.sqlalchemy_database_url),
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "url": _redact_database_url(settings.sqlalchemy_database_url),
            "error": str(exc),
        }


def pgvector_health() -> dict[str, Any]:
    try:
        with engine.connect() as connection:
            extension_installed = bool(
                connection.execute(
                    text(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                        ")"
                    )
                ).scalar()
            )
            column_type = connection.execute(
                text(
                    """
                    SELECT format_type(attribute.atttypid, attribute.atttypmod)
                    FROM pg_attribute attribute
                    JOIN pg_class table_class ON table_class.oid = attribute.attrelid
                    JOIN pg_namespace namespace ON namespace.oid = table_class.relnamespace
                    WHERE table_class.relname = 'knowledge_chunks'
                      AND namespace.nspname = current_schema()
                      AND attribute.attname = 'embedding'
                      AND NOT attribute.attisdropped
                    """
                )
            ).scalar()
            chunk_count = connection.execute(
                text("SELECT COUNT(*) FROM knowledge_chunks")
            ).scalar()
            embedded_chunk_count = connection.execute(
                text("SELECT COUNT(*) FROM knowledge_chunks WHERE embedding IS NOT NULL")
            ).scalar()
            index_count = connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM pg_indexes
                    WHERE schemaname = current_schema()
                      AND tablename = 'knowledge_chunks'
                      AND indexname IN (
                        'ix_knowledge_chunks_embedding',
                        'ix_knowledge_chunks_search_vector'
                      )
                    """
                )
            ).scalar()
    except Exception as exc:
        return {
            "status": "unavailable",
            "extension_installed": False,
            "error": str(exc),
        }

    storage_ready = extension_installed and str(column_type or "").startswith("vector")
    index_ready = int(index_count or 0) >= 2
    return {
        "status": "healthy" if storage_ready and index_ready else "unhealthy",
        "extension_installed": extension_installed,
        "embedding_column_type": column_type,
        "vector_index_present": index_ready,
        "chunk_count": int(chunk_count or 0),
        "embedded_chunk_count": int(embedded_chunk_count or 0),
        "expected_dimensions": settings.embedding_dimensions,
    }


def storage_health() -> dict[str, Any]:
    try:
        resolved = StorageService().ensure_ready()
        writable = all(
            os.access(path, os.W_OK) for key, path in resolved.items() if key.endswith("_dir")
        )
        return {
            "status": "healthy" if writable else "unhealthy",
            "writable": writable,
            **resolved,
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "writable": False,
            "storage_backend": settings.storage_backend,
            "error": str(exc),
        }


def readiness_report() -> dict[str, Any]:
    database = (
        database_health()
        if settings.startup_validate_database
        else {"status": "skipped", "database": "not_checked"}
    )
    storage = (
        storage_health()
        if settings.startup_validate_storage
        else {"status": "skipped"}
    )
    pgvector = (
        pgvector_health()
        if settings.startup_validate_pgvector
        else {"status": "skipped"}
    )

    statuses = [database["status"], storage["status"], pgvector["status"]]
    ready = all(status in {"healthy", "skipped"} for status in statuses)
    return {
        "status": "healthy" if ready else "unhealthy",
        "ready": ready,
        "environment": settings.environment,
        "database": database,
        "storage": storage,
        "pgvector": pgvector,
    }


def validate_startup_or_raise() -> dict[str, Any]:
    report = readiness_report()
    if not report["ready"]:
        failures = []
        for key in ("database", "storage", "pgvector"):
            component = report[key]
            if component["status"] in {"healthy", "skipped"}:
                continue
            failures.append(f"{key}: {component.get('error') or component['status']}")
        message = "; ".join(failures) or "startup validation failed"
        raise RuntimeError(message)
    return report


def _redact_database_url(database_url: str) -> str:
    if "@" not in database_url or "://" not in database_url:
        return database_url
    scheme, remainder = database_url.split("://", 1)
    if "@" not in remainder:
        return database_url
    credentials, host = remainder.split("@", 1)
    if ":" not in credentials:
        return f"{scheme}://***@{host}"
    username, _password = credentials.split(":", 1)
    return f"{scheme}://{username}:***@{host}"
