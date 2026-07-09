from __future__ import annotations

import logging
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.exceptions import KnowledgeEmbeddingError


logger = logging.getLogger(__name__)


class EmbeddingService:
    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key.strip())

    def health_check(self, *, live_check: bool = False) -> dict[str, Any]:
        status = {
            "provider": "gemini",
            "api_key_configured": self.is_configured(),
            "model": settings.gemini_embedding_model,
            "configured_dimensions": settings.embedding_dimensions,
            "request_timeout_seconds": settings.gemini_request_timeout_seconds,
            "live_check": live_check,
            "status": "configured" if self.is_configured() else "not_configured",
            "error": None,
        }
        if not self.is_configured():
            status["error"] = "GEMINI_API_KEY is not configured"
            return status
        if not live_check:
            return status

        try:
            embedding = self.embed_text("RAG embedding health check")
        except KnowledgeEmbeddingError as exc:
            status["status"] = "unavailable"
            status["error"] = str(exc)
            return status

        vector_dimensions = len(embedding or [])
        status["vector_dimensions"] = vector_dimensions
        if vector_dimensions != settings.embedding_dimensions:
            status["status"] = "dimension_mismatch"
            status["error"] = (
                f"Embedding returned {vector_dimensions} dimensions; "
                f"expected {settings.embedding_dimensions}"
            )
            return status

        status["status"] = "healthy"
        return status

    def embed_text(self, text: str) -> list[float] | None:
        if not self.is_configured():
            return None

        try:
            client = genai.Client(
                api_key=settings.gemini_api_key,
                http_options=types.HttpOptions(
                    timeout=settings.gemini_request_timeout_seconds * 1000,
                ),
            )
            response = client.models.embed_content(
                model=settings.gemini_embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=settings.embedding_dimensions,
                ),
            )
        except Exception as exc:
            logger.exception("Gemini embedding request failed")
            raise KnowledgeEmbeddingError("Embedding generation failed") from exc

        embedding = self._extract_embedding(response)
        if embedding is None:
            raise KnowledgeEmbeddingError("Embedding provider returned no vector")
        return embedding

    def _extract_embedding(self, response: Any) -> list[float] | None:
        embeddings = getattr(response, "embeddings", None)
        if embeddings:
            values = getattr(embeddings[0], "values", None)
            if values is not None:
                return [float(value) for value in values]

        embedding = getattr(response, "embedding", None)
        values = getattr(embedding, "values", None) if embedding is not None else None
        if values is not None:
            return [float(value) for value in values]
        return None

    def vector_literal(self, embedding: list[float] | None) -> str | None:
        if embedding is None:
            return None
        return "[" + ",".join(str(float(value)) for value in embedding) + "]"
