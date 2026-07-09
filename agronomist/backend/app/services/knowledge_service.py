from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeDocumentVersion
from app.repositories.knowledge_repository import KnowledgeRepository
from app.schemas.knowledge import (
    KnowledgeCitationRead,
    KnowledgeDryRunDocumentRead,
    KnowledgeSearchResponse,
    KnowledgeSearchResultRead,
)
from app.services.cache_service import TTLCache
from app.services.document_parser_service import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    DocumentParserService,
)
from app.services.embedding_service import EmbeddingService
from app.services.exceptions import (
    KnowledgeEmbeddingError,
    KnowledgeParseError,
    KnowledgePersistenceError,
    KnowledgeValidationError,
)
from app.services.storage_service import StorageService


logger = logging.getLogger(__name__)
knowledge_search_cache: TTLCache[KnowledgeSearchResponse] = TTLCache(
    settings.knowledge_search_cache_ttl_seconds,
)


@dataclass(frozen=True)
class IngestResult:
    documents: list[KnowledgeDocument]
    skipped_count: int
    errors: list[str]


@dataclass(frozen=True)
class DryRunIngestResult:
    documents: list[KnowledgeDryRunDocumentRead]
    skipped_count: int
    errors: list[str]


class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = KnowledgeRepository(db)
        self.parser = DocumentParserService()
        self.embedding_service = EmbeddingService()
        self.storage_service = StorageService()

    def list_documents(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ):
        try:
            return self.repository.list_documents(skip=skip, limit=limit)
        except SQLAlchemyError as exc:
            raise KnowledgePersistenceError from exc

    def ingest_path(
        self,
        *,
        path: Path,
        title: str | None,
        source_uri: str | None,
        language: str,
        metadata: dict[str, Any],
        user_id: uuid.UUID | None,
        force_reindex: bool = False,
    ) -> KnowledgeDocument:
        if not path.is_file():
            raise KnowledgeValidationError("Document path does not exist")

        parsed = self.parser.parse_path(path)
        checksum = self._checksum(parsed.text.encode("utf-8"))
        storage_path = self._store_document_file(path, checksum)
        resolved_source_uri = source_uri or str(path.resolve())
        existing_document = self._get_existing_document(resolved_source_uri)

        if existing_document is not None and existing_document.checksum == checksum and not force_reindex:
            return existing_document

        duplicate_document = self._get_duplicate_document(checksum)
        try:
            if existing_document is None:
                document = KnowledgeDocument(
                    title=title or parsed.title,
                    source_type="file",
                    source_uri=resolved_source_uri,
                    content_type=parsed.content_type,
                    language=language,
                    checksum=checksum,
                    duplicate_of_document_id=(
                        duplicate_document.id if duplicate_document is not None else None
                    ),
                    ingested_by_user_id=user_id,
                    document_metadata=metadata,
                )
                self.repository.add_document(document)
                self.db.flush()
            else:
                document = existing_document
                document.title = title or document.title
                document.content_type = parsed.content_type
                document.language = language
                document.checksum = checksum
                document.current_version += 1
                document.status = "active"
                document.document_metadata = {**document.document_metadata, **metadata}
                self.repository.deactivate_chunks(document_id=document.id)

            version = KnowledgeDocumentVersion(
                document_id=document.id,
                version_number=document.current_version,
                checksum=checksum,
                original_filename=path.name,
                storage_path=storage_path,
                parser=parsed.parser,
                extracted_text=parsed.text,
                word_count=parsed.word_count,
                version_metadata={"source_uri": resolved_source_uri},
            )
            self.repository.add_version(version)
            self.db.flush()
            self._index_chunks(document=document, version=version, text=parsed.text)
            self.db.commit()
            self.db.refresh(document)
            knowledge_search_cache.clear()
            return document
        except KnowledgeEmbeddingError:
            self.db.rollback()
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise KnowledgePersistenceError from exc

    def ingest_folder(
        self,
        *,
        folder_path: Path,
        language: str,
        metadata: dict[str, Any],
        user_id: uuid.UUID | None,
        recursive: bool,
        force_reindex: bool,
    ) -> IngestResult:
        if not folder_path.is_dir():
            raise KnowledgeValidationError("Folder path does not exist")

        iterator = folder_path.rglob("*") if recursive else folder_path.glob("*")
        documents: list[KnowledgeDocument] = []
        errors: list[str] = []
        skipped_count = 0
        for path in sorted(iterator):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_DOCUMENT_EXTENSIONS:
                continue
            try:
                document = self.ingest_path(
                    path=path,
                    title=None,
                    source_uri=str(path.resolve()),
                    language=language,
                    metadata=metadata,
                    user_id=user_id,
                    force_reindex=force_reindex,
                )
                documents.append(document)
            except (
                KnowledgeValidationError,
                KnowledgeParseError,
                KnowledgeEmbeddingError,
                KnowledgePersistenceError,
            ) as exc:
                skipped_count += 1
                errors.append(f"{path}: {exc}")
                logger.warning("Knowledge folder ingestion skipped %s: %s", path, exc)

        return IngestResult(
            documents=documents,
            skipped_count=skipped_count,
            errors=errors,
        )

    def dry_run_path(
        self,
        *,
        path: Path,
        title: str | None,
        source_uri: str | None,
        language: str,
        force_reindex: bool = False,
    ) -> KnowledgeDryRunDocumentRead:
        if not path.is_file():
            raise KnowledgeValidationError("Document path does not exist")

        parsed = self.parser.parse_path(path)
        checksum = self._checksum(parsed.text.encode("utf-8"))
        resolved_source_uri = source_uri or str(path.resolve())
        existing_document = self._get_existing_document(resolved_source_uri)
        duplicate_document = self._get_duplicate_document(checksum)
        unchanged = (
            existing_document is not None
            and existing_document.checksum == checksum
            and not force_reindex
        )

        return KnowledgeDryRunDocumentRead(
            source_uri=resolved_source_uri,
            title=title or parsed.title,
            content_type=parsed.content_type,
            parser=parsed.parser,
            language=language,
            word_count=parsed.word_count,
            chunk_count=len(self._chunk_text(parsed.text)),
            checksum=checksum,
            existing_document_id=existing_document.id if existing_document else None,
            duplicate_document_id=(
                duplicate_document.id if duplicate_document is not None else None
            ),
            would_create_document=existing_document is None,
            would_reindex=existing_document is not None and not unchanged,
            would_skip_unchanged=unchanged,
            embedding_configured=self.embedding_service.is_configured(),
        )

    def dry_run_folder(
        self,
        *,
        folder_path: Path,
        language: str,
        recursive: bool,
        force_reindex: bool,
    ) -> DryRunIngestResult:
        if not folder_path.is_dir():
            raise KnowledgeValidationError("Folder path does not exist")

        iterator = folder_path.rglob("*") if recursive else folder_path.glob("*")
        documents: list[KnowledgeDryRunDocumentRead] = []
        errors: list[str] = []
        skipped_count = 0
        for path in sorted(iterator):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_DOCUMENT_EXTENSIONS:
                continue
            try:
                documents.append(
                    self.dry_run_path(
                        path=path,
                        title=None,
                        source_uri=str(path.resolve()),
                        language=language,
                        force_reindex=force_reindex,
                    )
                )
            except (
                KnowledgeValidationError,
                KnowledgeParseError,
                KnowledgePersistenceError,
            ) as exc:
                skipped_count += 1
                errors.append(f"{path}: {exc}")
                logger.warning(
                    "Knowledge folder dry run skipped %s: %s",
                    path,
                    exc,
                )

        return DryRunIngestResult(
            documents=documents,
            skipped_count=skipped_count,
            errors=errors,
        )

    def search(
        self,
        *,
        query: str,
        limit: int = 8,
        language: str | None = None,
        content_type: str | None = None,
        use_hybrid: bool = True,
    ) -> KnowledgeSearchResponse:
        cache_key = f"{query}|{limit}|{language}|{content_type}|{use_hybrid}"
        cached = knowledge_search_cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(update={"cache_hit": True})

        embedding = self.embedding_service.embed_text(query)
        embedding_literal = self.embedding_service.vector_literal(embedding)
        try:
            rows = self.repository.hybrid_search(
                query=query,
                embedding_vector=embedding_literal,
                limit=limit,
                language=language,
                content_type=content_type,
                use_hybrid=use_hybrid,
            )
        except SQLAlchemyError as exc:
            raise KnowledgePersistenceError from exc

        results = [self._row_to_result(row) for row in rows]
        citations = [result.citation for result in results]
        response = KnowledgeSearchResponse(
            query=query,
            results=results,
            citations=citations,
            cache_hit=False,
        )
        knowledge_search_cache.set(cache_key, response)
        return response

    def build_rag_context(self, *, query: str, limit: int = 5) -> tuple[str, list[dict[str, Any]]]:
        try:
            response = self.search(query=query, limit=limit)
        except (KnowledgePersistenceError, KnowledgeEmbeddingError) as exc:
            logger.warning("Knowledge retrieval unavailable: %s", exc)
            return "", []

        if not response.results:
            return "", []

        lines = ["Knowledge/RAG context:"]
        citations: list[dict[str, Any]] = []
        for index, result in enumerate(response.results, start=1):
            lines.append(f"[{index}] {result.title} - {result.content}")
            citations.append(result.citation.model_dump(mode="json"))
        return "\n\n".join(lines), citations

    def _index_chunks(
        self,
        *,
        document: KnowledgeDocument,
        version: KnowledgeDocumentVersion,
        text: str,
    ) -> None:
        for index, chunk_text in enumerate(self._chunk_text(text)):
            embedding = self.embedding_service.embed_text(chunk_text)
            content_hash = self._checksum(chunk_text.encode("utf-8"))
            chunk = KnowledgeChunk(
                document_id=document.id,
                version_id=version.id,
                chunk_index=index,
                content=chunk_text,
                content_hash=content_hash,
                token_count=len(chunk_text.split()),
                embedding=embedding,
                embedding_model=settings.gemini_embedding_model if embedding else None,
                citation_label=f"{document.title} v{version.version_number} chunk {index + 1}",
                chunk_metadata={"version_number": version.version_number},
            )
            self.repository.add_chunk(chunk)

    def _chunk_text(self, text: str) -> list[str]:
        words = text.split()
        if not words:
            return []

        chunk_size = max(settings.knowledge_chunk_size, 200)
        overlap = min(settings.knowledge_chunk_overlap, chunk_size // 2)
        chunks: list[str] = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunks.append(" ".join(words[start:end]))
            if end == len(words):
                break
            start = max(end - overlap, start + 1)
        return chunks

    def _row_to_result(self, row: dict[str, Any]) -> KnowledgeSearchResultRead:
        citation = KnowledgeCitationRead(
            document_id=row["document_id"],
            version_id=row["version_id"],
            chunk_id=row["chunk_id"],
            title=row["title"],
            source_uri=row["source_uri"],
            citation_label=row["citation_label"],
        )
        return KnowledgeSearchResultRead(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            version_id=row["version_id"],
            title=row["title"],
            content=row["content"],
            score=float(row["score"] or 0),
            semantic_score=float(row["semantic_score"] or 0),
            lexical_score=float(row["lexical_score"] or 0),
            citation=citation,
        )

    def _store_document_file(self, path: Path, checksum: str) -> str:
        stored_file = self.storage_service.copy_file(
            source_path=path,
            configured_dir=settings.knowledge_storage_dir,
            relative_path=f"documents/{checksum}{path.suffix.lower()}",
        )
        return stored_file.storage_key

    def _get_existing_document(self, source_uri: str) -> KnowledgeDocument | None:
        try:
            return self.repository.get_document_by_source_uri(source_uri)
        except SQLAlchemyError as exc:
            raise KnowledgePersistenceError from exc

    def _get_duplicate_document(self, checksum: str) -> KnowledgeDocument | None:
        try:
            return self.repository.get_document_by_checksum(checksum)
        except SQLAlchemyError as exc:
            raise KnowledgePersistenceError from exc

    def _checksum(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
