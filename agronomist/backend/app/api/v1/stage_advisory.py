from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_farmer, get_stage_advisory_service
from app.models.user import User
from app.schemas.stage_advisory import StageAdvisoryRead
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    StageAdvisoryPersistenceError,
)
from app.services.stage_advisory_service import StageAdvisoryService


router = APIRouter(prefix="/farms/{farm_id}/stage-advisory", tags=["stage-advisory"])


@router.get("", response_model=StageAdvisoryRead)
def get_farm_stage_advisory(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    stage_advisory_service: StageAdvisoryService = Depends(
        get_stage_advisory_service,
    ),
) -> StageAdvisoryRead:
    try:
        return stage_advisory_service.get_stage_advisory(
            user_id=current_user.id,
            farm_id=farm_id,
        )
    except FarmNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )
    except StageAdvisoryPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to read crop stage advisory data",
        )
    except FarmPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch farm stage advisory",
        )
