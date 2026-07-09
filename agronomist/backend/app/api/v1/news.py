from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_active_user, get_intelligence_service
from app.models.user import User
from app.schemas.news import NewsArticleRead
from app.services.exceptions import IntelligencePersistenceError
from app.services.intelligence_service import IntelligenceService


router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=list[NewsArticleRead])
def get_news(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    article_type: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
) -> list[NewsArticleRead]:
    del current_user
    try:
        return list(
            intelligence_service.list_news(
                skip=skip,
                limit=limit,
                article_type=article_type,
            )
        )
    except IntelligencePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch news archive",
        )


@router.get("/latest", response_model=list[NewsArticleRead])
def get_latest_news(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
) -> list[NewsArticleRead]:
    del current_user
    try:
        return list(intelligence_service.latest(limit=limit))
    except IntelligencePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch latest news",
        )


@router.get("/crop/{crop}", response_model=list[NewsArticleRead])
def get_news_by_crop(
    crop: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
) -> list[NewsArticleRead]:
    del current_user
    try:
        return list(intelligence_service.by_crop(crop=crop, skip=skip, limit=limit))
    except IntelligencePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch crop news",
        )


@router.get("/state/{state}", response_model=list[NewsArticleRead])
def get_news_by_state(
    state: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
) -> list[NewsArticleRead]:
    del current_user
    try:
        return list(intelligence_service.by_state(state=state, skip=skip, limit=limit))
    except IntelligencePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch state news",
        )


@router.get("/search", response_model=list[NewsArticleRead])
def search_news(
    q: str = Query(min_length=1, max_length=1000),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
) -> list[NewsArticleRead]:
    del current_user
    try:
        return list(intelligence_service.search(query=q, skip=skip, limit=limit))
    except IntelligencePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to search news archive",
        )
