from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
)


class KnowledgeRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_document(self, document: KnowledgeDocument) -> KnowledgeDocument:
        self.db.add(document)
        return document

    def add_version(
        self,
        version: KnowledgeDocumentVersion,
    ) -> KnowledgeDocumentVersion:
        self.db.add(version)
        return version

    def add_chunk(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        self.db.add(chunk)
        return chunk

    def list_documents(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[KnowledgeDocument]:
        statement = (
            select(KnowledgeDocument)
            .order_by(KnowledgeDocument.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def get_document(self, document_id: uuid.UUID) -> KnowledgeDocument | None:
        statement = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_latest_version(
        self,
        *,
        document_id: uuid.UUID,
    ) -> KnowledgeDocumentVersion | None:
        statement = (
            select(KnowledgeDocumentVersion)
            .where(KnowledgeDocumentVersion.document_id == document_id)
            .order_by(KnowledgeDocumentVersion.version_number.desc())
            .limit(1)
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_document_by_source_uri(
        self,
        source_uri: str,
    ) -> KnowledgeDocument | None:
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.source_uri == source_uri,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_document_by_checksum(
        self,
        checksum: str,
    ) -> KnowledgeDocument | None:
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.checksum == checksum,
        )
        return self.db.execute(statement).scalars().first()

    def deactivate_chunks(self, *, document_id: uuid.UUID) -> None:
        statement = (
            update(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document_id)
            .values(is_active=False)
        )
        self.db.execute(statement)

    def hybrid_search(
        self,
        *,
        query: str,
        embedding_vector: str | None,
        limit: int,
        language: str | None,
        content_type: str | None,
        use_hybrid: bool,
    ) -> list[dict]:
        semantic_expr = "0.0"
        if embedding_vector is not None:
            semantic_expr = (
                "COALESCE(1 - (kc.embedding <=> CAST(:embedding AS vector)), 0.0)"
            )

        lexical_expr = (
            "COALESCE("
            "ts_rank_cd(kc.search_vector, plainto_tsquery('simple', :query)), "
            "0.0)"
        )
        score_expr = (
            f"(({semantic_expr}) * 0.65 + ({lexical_expr}) * 0.35)"
            if use_hybrid
            else f"({semantic_expr})"
        )
        if embedding_vector is None:
            score_expr = f"({lexical_expr})"

        filters = ["kc.is_active = true", "kd.status = 'active'"]
        params = {
            "query": query,
            "embedding": embedding_vector,
            "limit": limit,
            "language": language,
            "content_type": content_type,
        }
        if language:
            filters.append("kd.language = :language")
        if content_type:
            filters.append("kd.content_type = :content_type")

        sql = text(
            f"""
            SELECT
                kc.id AS chunk_id,
                kc.document_id,
                kc.version_id,
                kd.title,
                kd.source_uri,
                kc.content,
                kc.citation_label,
                ({semantic_expr}) AS semantic_score,
                ({lexical_expr}) AS lexical_score,
                {score_expr} AS score
            FROM knowledge_chunks kc
            JOIN knowledge_documents kd ON kd.id = kc.document_id
            WHERE {' AND '.join(filters)}
              AND (
                kc.search_vector @@ plainto_tsquery('simple', :query)
                OR (:embedding IS NOT NULL AND kc.embedding IS NOT NULL)
              )
            ORDER BY score DESC, kc.created_at DESC
            LIMIT :limit
            """
        )
        rows = self.db.execute(sql, params).mappings().all()
        return [dict(row) for row in rows]
