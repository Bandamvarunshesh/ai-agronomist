from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.intelligence import IntelligenceSource, NewsArticle
from app.repositories.intelligence_repository import IntelligenceRepository
from app.schemas.news import (
    IntelligenceSourceConfigEntry,
    IntelligenceSourceConfigLoadResponse,
)
from app.services.cache_service import TTLCache
from app.services.exceptions import IntelligencePersistenceError, IntelligenceSourceError


logger = logging.getLogger(__name__)
news_cache: TTLCache[list[NewsArticle]] = TTLCache(settings.news_cache_ttl_seconds)


@dataclass(frozen=True)
class ParsedArticle:
    title: str
    url: str
    summary: str | None
    content: str | None
    published_at: datetime | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class IntelligenceSourceSyncReport:
    source_id: uuid.UUID | None
    source_name: str
    source_url: str
    source_type: str
    source_format: str
    dry_run: bool
    fetched: bool
    parsed_count: int
    duplicate_count: int
    would_create_count: int
    created_count: int
    status: str
    error: str | None = None


@dataclass(frozen=True)
class ExtractedLink:
    title: str
    url: str


class AnchorExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[ExtractedLink] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a" or self._href is not None:
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        if href:
            self._href = href
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        title = " ".join(" ".join(self._text_parts).split())
        if title:
            self.links.append(ExtractedLink(title=title, url=self._href))
        self._href = None
        self._text_parts = []


class IntelligenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = IntelligenceRepository(db)

    def list_sources(self, *, skip: int = 0, limit: int = 100):
        try:
            return self.repository.list_sources(skip=skip, limit=limit)
        except SQLAlchemyError as exc:
            raise IntelligencePersistenceError from exc

    def load_sources_from_config(
        self,
        *,
        config_path: Path | None = None,
        dry_run: bool = True,
    ) -> IntelligenceSourceConfigLoadResponse:
        path = self._resolve_config_path(config_path)
        payload = self._read_source_config(path)
        source_entries = payload.get("sources")
        if not isinstance(source_entries, list):
            raise IntelligenceSourceError("Source config must contain a sources list")

        errors: list[str] = []
        warnings: list[str] = []
        valid_sources: list[IntelligenceSourceConfigEntry] = []
        seen_urls: set[str] = set()
        for index, source_data in enumerate(source_entries):
            try:
                source_in = IntelligenceSourceConfigEntry.model_validate(source_data)
            except ValidationError as exc:
                errors.append(f"sources[{index}]: {exc.errors()}")
                continue
            if source_in.url in seen_urls:
                errors.append(f"sources[{index}]: duplicate url in config")
                continue
            seen_urls.add(source_in.url)
            if not source_in.is_active:
                warnings.append(f"sources[{index}]: source is inactive")
            valid_sources.append(source_in)

        if dry_run or errors:
            return IntelligenceSourceConfigLoadResponse(
                config_path=str(path),
                dry_run=dry_run,
                source_count=len(valid_sources),
                upserted_count=0,
                errors=errors,
                warnings=warnings,
            )

        upserted_count = 0
        try:
            for source_in in valid_sources:
                existing = self.repository.get_source_by_url(source_in.url)
                if existing is None:
                    source = IntelligenceSource(
                        name=source_in.name,
                        source_type=source_in.source_type,
                        source_format=source_in.source_format,
                        url=source_in.url,
                        language=source_in.language,
                        country=source_in.country,
                        state=source_in.state,
                        district=source_in.district,
                        crop_tags=source_in.crop_tags,
                        credibility_score=source_in.credibility_score,
                        is_active=source_in.is_active,
                        source_metadata=source_in.source_metadata,
                    )
                    self.repository.add_source(source)
                else:
                    existing.name = source_in.name
                    existing.source_type = source_in.source_type
                    existing.source_format = source_in.source_format
                    existing.language = source_in.language
                    existing.country = source_in.country
                    existing.state = source_in.state
                    existing.district = source_in.district
                    existing.crop_tags = source_in.crop_tags
                    existing.credibility_score = source_in.credibility_score
                    existing.is_active = source_in.is_active
                    existing.source_metadata = source_in.source_metadata
                upserted_count += 1
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise IntelligencePersistenceError from exc

        return IntelligenceSourceConfigLoadResponse(
            config_path=str(path),
            dry_run=False,
            source_count=len(valid_sources),
            upserted_count=upserted_count,
            errors=[],
            warnings=warnings,
        )

    def sync_all_sources(self) -> int:
        reports = self.sync_all_sources_report(dry_run=False)
        return sum(report.created_count for report in reports)

    def sync_all_sources_report(
        self,
        *,
        dry_run: bool,
    ) -> list[IntelligenceSourceSyncReport]:
        try:
            sources = self.repository.list_active_sources()
        except SQLAlchemyError as exc:
            raise IntelligencePersistenceError from exc

        reports: list[IntelligenceSourceSyncReport] = []
        for source in sources:
            try:
                reports.append(self._sync_source_to_report(source, dry_run=dry_run))
            except (IntelligenceSourceError, IntelligencePersistenceError) as exc:
                logger.exception("Intelligence source sync failed: source_id=%s", source.id)
                reports.append(
                    IntelligenceSourceSyncReport(
                        source_id=source.id,
                        source_name=source.name,
                        source_url=source.url,
                        source_type=source.source_type,
                        source_format=source.source_format,
                        dry_run=dry_run,
                        fetched=False,
                        parsed_count=0,
                        duplicate_count=0,
                        would_create_count=0,
                        created_count=0,
                        status="failed",
                        error=str(exc),
                    )
                )
                if not dry_run:
                    source.last_synced_at = datetime.now(timezone.utc)
                    source.source_metadata = {
                        **source.source_metadata,
                        "last_error": str(exc),
                    }
                    self.db.commit()
        return reports

    def sync_source(self, source: IntelligenceSource) -> int:
        return self._sync_source_to_report(source, dry_run=False).created_count

    def _sync_source_to_report(
        self,
        source: IntelligenceSource,
        *,
        dry_run: bool,
    ) -> IntelligenceSourceSyncReport:
        payload = self._fetch(source.url)
        articles = self._parse_source(source=source, payload=payload)
        created_count = 0
        duplicate_count = 0
        would_create_count = 0

        try:
            for parsed in articles:
                if self.repository.get_article_by_url(parsed.url) is not None:
                    duplicate_count += 1
                    continue
                content_hash = self._article_hash(parsed)
                if self.repository.get_article_by_hash(content_hash) is not None:
                    duplicate_count += 1
                    continue
                if dry_run:
                    would_create_count += 1
                    continue
                article = NewsArticle(
                    source_id=source.id,
                    source_name=source.name,
                    article_type=source.source_type,
                    title=parsed.title,
                    summary=parsed.summary,
                    content=parsed.content,
                    url=parsed.url,
                    language=source.language,
                    category=self._categorize(source, parsed),
                    crop_tags=self._crop_tags(source, parsed),
                    state_tags=self._state_tags(source, parsed),
                    district_tags=self._district_tags(source, parsed),
                    credibility_score=source.credibility_score,
                    content_hash=content_hash,
                    published_at=parsed.published_at,
                    fetched_at=datetime.now(timezone.utc),
                    article_metadata=parsed.metadata,
                )
                self.repository.add_article(article)
                created_count += 1
            if not dry_run:
                source.last_synced_at = datetime.now(timezone.utc)
                source.source_metadata = {
                    **source.source_metadata,
                    "last_sync_created_count": created_count,
                    "last_error": None,
                }
                self.db.commit()
                news_cache.clear()
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise IntelligencePersistenceError from exc

        return IntelligenceSourceSyncReport(
            source_id=source.id,
            source_name=source.name,
            source_url=source.url,
            source_type=source.source_type,
            source_format=source.source_format,
            dry_run=dry_run,
            fetched=True,
            parsed_count=len(articles),
            duplicate_count=duplicate_count,
            would_create_count=would_create_count,
            created_count=created_count,
            status="ok",
            error=None,
        )

    def list_news(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        article_type: str | None = None,
    ):
        cache_key = f"news:{skip}:{limit}:{article_type}"
        cached = news_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            articles = list(
                self.repository.list_articles(
                    skip=skip,
                    limit=limit,
                    article_type=article_type,
                )
            )
        except SQLAlchemyError as exc:
            raise IntelligencePersistenceError from exc
        news_cache.set(cache_key, articles)
        return articles

    def latest(self, *, limit: int = 20):
        return self.list_news(limit=limit)

    def by_crop(self, *, crop: str, skip: int = 0, limit: int = 50):
        cache_key = f"crop:{crop.lower()}:{skip}:{limit}"
        cached = news_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            articles = list(
                self.repository.list_by_crop(
                    crop=crop,
                    skip=skip,
                    limit=limit,
                )
            )
        except SQLAlchemyError as exc:
            raise IntelligencePersistenceError from exc
        news_cache.set(cache_key, articles)
        return articles

    def by_state(self, *, state: str, skip: int = 0, limit: int = 50):
        cache_key = f"state:{state.lower()}:{skip}:{limit}"
        cached = news_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            articles = list(
                self.repository.list_by_state(
                    state=state,
                    skip=skip,
                    limit=limit,
                )
            )
        except SQLAlchemyError as exc:
            raise IntelligencePersistenceError from exc
        news_cache.set(cache_key, articles)
        return articles

    def search(self, *, query: str, skip: int = 0, limit: int = 50):
        try:
            return self.repository.search(query=query, skip=skip, limit=limit)
        except SQLAlchemyError as exc:
            raise IntelligencePersistenceError from exc

    def _resolve_config_path(self, config_path: Path | None) -> Path:
        path = config_path or Path(settings.intelligence_source_config_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        return path.expanduser().resolve()

    def _read_source_config(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise IntelligenceSourceError(f"Source config file not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise IntelligenceSourceError("Source config file must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise IntelligenceSourceError("Source config root must be a JSON object")
        return payload

    def _fetch(self, url: str) -> bytes:
        last_error: Exception | None = None
        for attempt in range(settings.intelligence_request_retries):
            try:
                request = Request(url, headers={"User-Agent": "ai-agronomist/0.1"})
                with urlopen(
                    request,
                    timeout=settings.intelligence_request_timeout_seconds,
                ) as response:
                    return response.read()
            except (HTTPError, URLError, TimeoutError) as exc:
                last_error = exc
                time.sleep(min(2**attempt, 8))
        raise IntelligenceSourceError(f"Unable to fetch source: {url}") from last_error

    def _parse_source(
        self,
        *,
        source: IntelligenceSource,
        payload: bytes,
    ) -> list[ParsedArticle]:
        source_format = source.source_format.lower()
        if source_format in {"rss", "atom", "xml"}:
            return self._parse_rss_or_atom(source, payload)
        if source_format == "json":
            return self._parse_json(source, payload)
        if source_format == "html":
            return self._parse_html(source, payload)
        raise IntelligenceSourceError(f"Unsupported source format: {source.source_format}")

    def _parse_rss_or_atom(
        self,
        source: IntelligenceSource,
        payload: bytes,
    ) -> list[ParsedArticle]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise IntelligenceSourceError("Invalid RSS/Atom XML") from exc

        items = root.findall(".//item")
        if not items:
            items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

        articles: list[ParsedArticle] = []
        for item in items:
            title = self._xml_text(item, "title")
            url = self._xml_text(item, "link")
            if not url:
                link = item.find("{http://www.w3.org/2005/Atom}link")
                url = link.attrib.get("href") if link is not None else ""
            if not title or not url:
                continue
            summary = self._xml_text(item, "description") or self._xml_text(item, "summary")
            published = (
                self._xml_text(item, "pubDate")
                or self._xml_text(item, "published")
                or self._xml_text(item, "updated")
            )
            articles.append(
                ParsedArticle(
                    title=title,
                    url=url,
                    summary=self._clean_text(summary),
                    content=None,
                    published_at=self._parse_datetime(published),
                    metadata={"source_format": source.source_format},
                )
            )
        return articles

    def _parse_json(self, source: IntelligenceSource, payload: bytes) -> list[ParsedArticle]:
        try:
            data = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise IntelligenceSourceError("Invalid JSON source") from exc

        items_path = source.source_metadata.get("items_path", "items")
        items = self._resolve_metadata_path(data, str(items_path))
        if items is None and isinstance(data, list):
            items = data
        if items is None:
            items = []
        if not isinstance(items, list):
            raise IntelligenceSourceError("JSON source items path must resolve to a list")

        field_map = source.source_metadata.get("field_map", {})
        if not isinstance(field_map, dict):
            field_map = {}

        articles: list[ParsedArticle] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(
                self._mapped_value(item, field_map, "title", ["title"]) or "",
            ).strip()
            url = str(
                self._mapped_value(item, field_map, "url", ["url", "link"]) or "",
            ).strip()
            if not title or not url:
                continue
            articles.append(
                ParsedArticle(
                    title=title,
                    url=url,
                    summary=self._clean_text(
                        self._mapped_value(
                            item,
                            field_map,
                            "summary",
                            ["summary", "description"],
                        ),
                    ),
                    content=self._clean_text(
                        self._mapped_value(item, field_map, "content", ["content"]),
                    ),
                    published_at=self._parse_datetime(
                        self._mapped_value(
                            item,
                            field_map,
                            "published_at",
                            ["published_at", "date"],
                        ),
                    ),
                    metadata={"source_format": source.source_format},
                )
            )
        return articles

    def _parse_html(self, source: IntelligenceSource, payload: bytes) -> list[ParsedArticle]:
        html_text = payload.decode("utf-8", errors="ignore")
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            links = self._extract_links_with_stdlib(html_text)
        else:
            soup = BeautifulSoup(html_text, "html.parser")
            links = [
                ExtractedLink(
                    title=" ".join(anchor.get_text(" ").split()),
                    url=anchor["href"],
                )
                for anchor in soup.find_all("a", href=True)
            ]

        articles: list[ParsedArticle] = []
        for link in links:
            if len(link.title) < 12:
                continue
            articles.append(
                ParsedArticle(
                    title=link.title,
                    url=urljoin(source.url, link.url),
                    summary=None,
                    content=None,
                    published_at=None,
                    metadata={"source_format": source.source_format},
                )
            )
        return articles

    def _extract_links_with_stdlib(self, html_text: str) -> list[ExtractedLink]:
        parser = AnchorExtractor()
        parser.feed(html_text)
        return parser.links

    def _resolve_metadata_path(self, value: Any, path: str) -> Any:
        current = value
        for part in path.split("."):
            if not part:
                continue
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if index < len(current) else None
            else:
                return None
            if current is None:
                return None
        return current

    def _mapped_value(
        self,
        item: dict[str, Any],
        field_map: dict[str, Any],
        canonical_field: str,
        fallback_fields: list[str],
    ) -> Any:
        configured_field = field_map.get(canonical_field)
        candidates = [configured_field] if configured_field else []
        candidates.extend(fallback_fields)
        for candidate in candidates:
            if not candidate:
                continue
            value = self._resolve_metadata_path(item, str(candidate))
            if value is not None:
                return value
        return None

    def _categorize(self, source: IntelligenceSource, article: ParsedArticle) -> str | None:
        categories = source.source_metadata.get("categories", {})
        text = f"{article.title} {article.summary or ''} {article.content or ''}".lower()
        if isinstance(categories, dict):
            for category, keywords in categories.items():
                if isinstance(keywords, list) and any(str(keyword).lower() in text for keyword in keywords):
                    return str(category)
        return source.source_type

    def _crop_tags(self, source: IntelligenceSource, article: ParsedArticle) -> list[str]:
        tags = {str(tag).lower() for tag in source.crop_tags}
        crop_keywords = source.source_metadata.get("crop_keywords", {})
        text = f"{article.title} {article.summary or ''} {article.content or ''}".lower()
        if isinstance(crop_keywords, dict):
            for crop, keywords in crop_keywords.items():
                if isinstance(keywords, list) and any(str(keyword).lower() in text for keyword in keywords):
                    tags.add(str(crop).lower())
        return sorted(tags)

    def _state_tags(self, source: IntelligenceSource, article: ParsedArticle) -> list[str]:
        tags = {source.state.lower()} if source.state else set()
        state_keywords = source.source_metadata.get("state_keywords", {})
        text = f"{article.title} {article.summary or ''} {article.content or ''}".lower()
        if isinstance(state_keywords, dict):
            for state, keywords in state_keywords.items():
                if isinstance(keywords, list) and any(str(keyword).lower() in text for keyword in keywords):
                    tags.add(str(state).lower())
        return sorted(tags)

    def _district_tags(self, source: IntelligenceSource, article: ParsedArticle) -> list[str]:
        tags = {source.district.lower()} if source.district else set()
        district_keywords = source.source_metadata.get("district_keywords", {})
        text = f"{article.title} {article.summary or ''} {article.content or ''}".lower()
        if isinstance(district_keywords, dict):
            for district, keywords in district_keywords.items():
                if isinstance(keywords, list) and any(str(keyword).lower() in text for keyword in keywords):
                    tags.add(str(district).lower())
        return sorted(tags)

    def _article_hash(self, article: ParsedArticle) -> str:
        content = "|".join(
            [
                article.title.strip().lower(),
                article.url.strip().lower(),
                article.summary or "",
                article.content or "",
            ]
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _xml_text(self, element: ET.Element, tag: str) -> str:
        found = element.find(tag)
        if found is None:
            found = element.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
        return " ".join((found.text or "").split()) if found is not None else ""

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = " ".join(str(value).split())
        return text or None

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = parsedate_to_datetime(str(value))
        except (TypeError, ValueError):
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
