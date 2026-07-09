from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_admin, get_intelligence_service
from app.models.user import User
from app.schemas.news import (
    IntelligenceSourceConfigLoadResponse,
    IntelligenceSourceRead,
    IntelligenceSourceSyncResponse,
)
from app.services.exceptions import IntelligencePersistenceError, IntelligenceSourceError
from app.services.intelligence_service import IntelligenceService


router = APIRouter(prefix="/admin/intelligence", tags=["admin-intelligence"])


@router.get("/sources", response_model=list[IntelligenceSourceRead])
def list_intelligence_sources(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_admin),
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
) -> list[IntelligenceSourceRead]:
    del current_user
    try:
        return list(intelligence_service.list_sources(skip=skip, limit=limit))
    except IntelligencePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch intelligence sources",
        )


@router.post(
    "/sources/load-config",
    response_model=IntelligenceSourceConfigLoadResponse,
)
def load_intelligence_source_config(
    config_path: Optional[str] = Query(default=None, max_length=2048),
    dry_run: bool = Query(default=True),
    current_user: User = Depends(get_current_admin),
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
) -> IntelligenceSourceConfigLoadResponse:
    del current_user
    try:
        return intelligence_service.load_sources_from_config(
            config_path=Path(config_path) if config_path else None,
            dry_run=dry_run,
        )
    except IntelligenceSourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except IntelligencePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to persist intelligence source configuration",
        )


@router.post("/sources/sync", response_model=IntelligenceSourceSyncResponse)
def sync_intelligence_sources(
    dry_run: bool = Query(default=True),
    current_user: User = Depends(get_current_admin),
    intelligence_service: IntelligenceService = Depends(get_intelligence_service),
) -> IntelligenceSourceSyncResponse:
    del current_user
    try:
        reports = intelligence_service.sync_all_sources_report(dry_run=dry_run)
    except IntelligencePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to read intelligence source configuration",
        )

    return IntelligenceSourceSyncResponse(
        dry_run=dry_run,
        source_count=len(reports),
        created_count=sum(report.created_count for report in reports),
        reports=list(reports),
    )
