from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_farmer, get_timeline_service
from app.models.user import User
from app.schemas.timeline import TimelineEventRead
from app.services.exceptions import FarmNotFoundError, TimelinePersistenceError
from app.services.timeline_service import TimelineService


router = APIRouter(prefix="/farms/{farm_id}/timeline", tags=["timeline"])


@router.get("", response_model=list[TimelineEventRead])
def get_farm_timeline(
    farm_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_farmer),
    timeline_service: TimelineService = Depends(get_timeline_service),
) -> list[TimelineEventRead]:
    try:
        return list(
            timeline_service.list_events(
                user_id=current_user.id,
                farm_id=farm_id,
                skip=skip,
                limit=limit,
            )
        )
    except FarmNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )
    except TimelinePersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch farm timeline",
        )
