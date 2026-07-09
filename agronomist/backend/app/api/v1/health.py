from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.embedding_service import EmbeddingService


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint that verifies database connectivity."""
    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@router.get("/embeddings")
def embedding_health_check(
    live_check: bool = Query(default=False),
):
    """Check Gemini embedding configuration and optional live provider access."""
    return EmbeddingService().health_check(live_check=live_check)


@router.get("/rag")
def rag_health_check(
    live_embedding_check: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """Check RAG dependencies: Gemini embeddings and pgvector storage."""
    embedding = EmbeddingService().health_check(live_check=live_embedding_check)
    pgvector = _pgvector_health(db)
    status = "healthy"
    if pgvector["status"] != "healthy":
        status = "unhealthy"
    elif embedding["status"] in {"not_configured", "unavailable", "dimension_mismatch"}:
        status = "degraded"

    return {
        "status": status,
        "embedding": embedding,
        "pgvector": pgvector,
        "knowledge": {
            "chunk_size": settings.knowledge_chunk_size,
            "chunk_overlap": settings.knowledge_chunk_overlap,
            "search_cache_ttl_seconds": settings.knowledge_search_cache_ttl_seconds,
        },
    }


def _pgvector_health(db: Session) -> dict:
    try:
        extension_installed = bool(
            db.execute(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                    ")"
                )
            ).scalar()
        )
        column_type = db.execute(
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
        chunk_count = db.execute(text("SELECT COUNT(*) FROM knowledge_chunks")).scalar()
        embedded_chunk_count = db.execute(
            text("SELECT COUNT(*) FROM knowledge_chunks WHERE embedding IS NOT NULL")
        ).scalar()
        index_count = db.execute(
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
