from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.core.health_checks import (
    pgvector_health,
    readiness_report,
    storage_health,
)
from app.core.config import settings
from app.services.embedding_service import EmbeddingService


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """General health status for monitors and operator dashboards."""
    readiness = readiness_report()
    return {
        "status": readiness["status"],
        "database": readiness["database"]["database"],
        "environment": readiness["environment"],
        "storage": readiness["storage"],
        "pgvector": readiness["pgvector"],
    }


@router.get("/live")
async def liveness_check():
    """Container/process liveness endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
    }


@router.get("/ready")
async def readiness_check():
    """Deployment readiness endpoint used by Render and external monitors."""
    readiness = readiness_report()
    status_code = 200 if readiness["ready"] else 503
    return JSONResponse(status_code=status_code, content=readiness)


@router.get("/embeddings")
def embedding_health_check(
    live_check: bool = Query(default=False),
):
    """Check Gemini embedding configuration and optional live provider access."""
    return EmbeddingService().health_check(live_check=live_check)


@router.get("/rag")
def rag_health_check(
    live_embedding_check: bool = Query(default=False),
):
    """Check RAG dependencies: Gemini embeddings and pgvector storage."""
    embedding = EmbeddingService().health_check(live_check=live_embedding_check)
    pgvector = pgvector_health()
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
        "storage": storage_health(),
    }
