from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KnowledgeDocumentIngestRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    source_uri: Optional[str] = Field(default=None, max_length=2048)
    folder_path: Optional[str] = Field(default=None, max_length=2048)
    language: str = Field(default="en", min_length=1, max_length=16)
    metadata: dict[str, Any] = Field(default_factory=dict)
    recursive: bool = True
    force_reindex: bool = False


class KnowledgeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    source_type: str
    source_uri: Optional[str]
    content_type: str
    language: str
    status: str
    current_version: int
    checksum: str
    duplicate_of_document_id: Optional[uuid.UUID]
    ingested_by_user_id: Optional[uuid.UUID]
    document_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=8, ge=1, le=20)
    language: Optional[str] = Field(default=None, max_length=16)
    content_type: Optional[str] = Field(default=None, max_length=100)
    use_hybrid: bool = True


class KnowledgeCitationRead(BaseModel):
    document_id: uuid.UUID
    version_id: uuid.UUID
    chunk_id: uuid.UUID
    title: str
    source_uri: Optional[str]
    citation_label: str


class KnowledgeSearchResultRead(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    version_id: uuid.UUID
    title: str
    content: str
    score: float
    semantic_score: float
    lexical_score: float
    citation: KnowledgeCitationRead


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeSearchResultRead]
    citations: list[KnowledgeCitationRead]
    cache_hit: bool = False


class KnowledgeDryRunDocumentRead(BaseModel):
    source_uri: str
    title: str
    content_type: str
    parser: str
    language: str
    word_count: int
    chunk_count: int
    checksum: str
    existing_document_id: Optional[uuid.UUID]
    duplicate_document_id: Optional[uuid.UUID]
    would_create_document: bool
    would_reindex: bool
    would_skip_unchanged: bool
    embedding_configured: bool


class KnowledgeBulkIngestResponse(BaseModel):
    documents: list[KnowledgeDocumentRead]
    ingested_count: int
    skipped_count: int
    errors: list[str] = Field(default_factory=list)
    dry_run: bool = False
    dry_run_documents: list[KnowledgeDryRunDocumentRead] = Field(default_factory=list)

    @model_validator(mode="after")
    def set_counts(self):
        self.ingested_count = len(self.documents)
        return self
