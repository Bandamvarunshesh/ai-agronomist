from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.vector import Vector


class KnowledgeDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_uri: Mapped[Optional[str]] = mapped_column(String(2048), index=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    language: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="en",
        server_default=text("'en'"),
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=text("'active'"),
        index=True,
    )
    current_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    duplicate_of_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"),
        index=True,
    )
    ingested_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    document_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    versions: Mapped[list["KnowledgeDocumentVersion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    duplicate_of: Mapped[Optional["KnowledgeDocument"]] = relationship(
        remote_side="KnowledgeDocument.id",
    )


class KnowledgeDocumentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    storage_path: Mapped[Optional[str]] = mapped_column(String(2048))
    parser: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    version_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    document: Mapped["KnowledgeDocument"] = relationship(back_populates="versions")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class KnowledgeChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(settings.embedding_dimensions),
        nullable=True,
    )
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100))
    citation_label: Mapped[str] = mapped_column(String(255), nullable=False)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )

    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")
    version: Mapped["KnowledgeDocumentVersion"] = relationship(back_populates="chunks")
