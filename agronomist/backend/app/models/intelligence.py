from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class IntelligenceSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "intelligence_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_format: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="rss",
        server_default=text("'rss'"),
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    language: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="en",
        server_default=text("'en'"),
        index=True,
    )
    country: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    crop_tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    credibility_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("0.5000"),
        server_default=text("0.5000"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    articles: Mapped[list["NewsArticle"]] = relationship(back_populates="source")


class NewsArticle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "news_articles"

    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intelligence_sources.id", ondelete="SET NULL"),
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    article_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    language: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="en",
        server_default=text("'en'"),
        index=True,
    )
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    crop_tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    state_tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    district_tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    credibility_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        index=True,
    )
    article_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    source: Mapped[Optional["IntelligenceSource"]] = relationship(back_populates="articles")
