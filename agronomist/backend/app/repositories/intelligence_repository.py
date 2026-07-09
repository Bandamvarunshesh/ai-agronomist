from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.models.farm import Farm
from app.models.intelligence import IntelligenceSource, NewsArticle


class IntelligenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_article(self, article: NewsArticle) -> NewsArticle:
        self.db.add(article)
        return article

    def add_source(self, source: IntelligenceSource) -> IntelligenceSource:
        self.db.add(source)
        return source

    def list_sources(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[IntelligenceSource]:
        statement = (
            select(IntelligenceSource)
            .order_by(IntelligenceSource.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def list_active_sources(self) -> Sequence[IntelligenceSource]:
        statement = select(IntelligenceSource).where(
            IntelligenceSource.is_active.is_(True),
        )
        return self.db.execute(statement).scalars().all()

    def list_active_sources_for_types(
        self,
        source_types: set[str],
    ) -> Sequence[IntelligenceSource]:
        statement = select(IntelligenceSource).where(
            IntelligenceSource.is_active.is_(True),
            IntelligenceSource.source_type.in_(sorted(source_types)),
        )
        return self.db.execute(statement).scalars().all()

    def get_source_by_url(self, url: str) -> IntelligenceSource | None:
        statement = select(IntelligenceSource).where(IntelligenceSource.url == url)
        return self.db.execute(statement).scalar_one_or_none()

    def get_article_by_url(self, url: str) -> NewsArticle | None:
        statement = select(NewsArticle).where(NewsArticle.url == url)
        return self.db.execute(statement).scalar_one_or_none()

    def get_article_by_hash(self, content_hash: str) -> NewsArticle | None:
        statement = select(NewsArticle).where(NewsArticle.content_hash == content_hash)
        return self.db.execute(statement).scalars().first()

    def list_articles(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        article_type: str | None = None,
    ) -> Sequence[NewsArticle]:
        statement = select(NewsArticle)
        if article_type is not None:
            statement = statement.where(NewsArticle.article_type == article_type)
        statement = (
            statement.order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.fetched_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def list_by_crop(
        self,
        *,
        crop: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[NewsArticle]:
        statement = (
            select(NewsArticle)
            .where(NewsArticle.crop_tags.contains([crop.lower()]))
            .order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.fetched_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def list_by_state(
        self,
        *,
        state: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[NewsArticle]:
        statement = (
            select(NewsArticle)
            .where(NewsArticle.state_tags.contains([state.lower()]))
            .order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.fetched_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def search(
        self,
        *,
        query: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[NewsArticle]:
        id_sql = text(
            """
            SELECT id FROM news_articles
            WHERE search_vector @@ plainto_tsquery('simple', :query)
               OR title ILIKE :like_query
               OR summary ILIKE :like_query
            ORDER BY ts_rank_cd(search_vector, plainto_tsquery('simple', :query)) DESC,
                     published_at DESC NULLS LAST,
                     fetched_at DESC
            OFFSET :skip LIMIT :limit
            """
        )
        ids = self.db.execute(
            id_sql,
            {
                "query": query,
                "like_query": f"%{query}%",
                "skip": skip,
                "limit": limit,
            },
        ).scalars().all()
        if not ids:
            return []

        statement = (
            select(NewsArticle)
            .where(NewsArticle.id.in_(ids))
            .order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.fetched_at.desc())
        )
        articles = self.db.execute(statement).scalars().all()
        article_map = {article.id: article for article in articles}
        return [article_map[article_id] for article_id in ids if article_id in article_map]

    def list_recent_for_farm_context(
        self,
        *,
        farm: Farm,
        article_types: set[str],
        limit: int = 30,
    ) -> Sequence[NewsArticle]:
        crop = farm.crop.lower()
        district = farm.district.lower()
        state = farm.state.lower()
        statement = (
            select(NewsArticle)
            .where(NewsArticle.article_type.in_(sorted(article_types)))
            .where(
                or_(
                    NewsArticle.crop_tags.contains([crop]),
                    NewsArticle.district_tags.contains([district]),
                    NewsArticle.state_tags.contains([state]),
                    NewsArticle.title.ilike(f"%{farm.crop}%"),
                    NewsArticle.summary.ilike(f"%{farm.crop}%"),
                    NewsArticle.title.ilike(f"%{farm.district}%"),
                    NewsArticle.summary.ilike(f"%{farm.district}%"),
                    NewsArticle.title.ilike(f"%{farm.state}%"),
                    NewsArticle.summary.ilike(f"%{farm.state}%"),
                )
            )
            .order_by(
                NewsArticle.published_at.desc().nullslast(),
                NewsArticle.fetched_at.desc(),
            )
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()
