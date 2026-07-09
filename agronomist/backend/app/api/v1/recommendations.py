from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_farmer, get_recommendation_engine_service
from app.models.user import User
from app.schemas.recommendation import FarmRecommendationRead
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    RecommendationConfigurationError,
    RecommendationContextError,
    RecommendationPersistenceError,
    RecommendationProviderError,
    RecommendationResponseParseError,
)
from app.services.recommendation_engine_service import RecommendationEngineService


router = APIRouter(prefix="/farms/{farm_id}/recommendations", tags=["recommendations"])


@router.get("", response_model=list[FarmRecommendationRead])
def get_farm_recommendations(
    farm_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_farmer),
    recommendation_service: RecommendationEngineService = Depends(
        get_recommendation_engine_service,
    ),
) -> list[FarmRecommendationRead]:
    try:
        return list(
            recommendation_service.list_recommendations(
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
    except (FarmPersistenceError, RecommendationPersistenceError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch farm recommendations",
        )


@router.post(
    "/generate",
    response_model=FarmRecommendationRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_farm_recommendation(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    recommendation_service: RecommendationEngineService = Depends(
        get_recommendation_engine_service,
    ),
) -> FarmRecommendationRead:
    try:
        return recommendation_service.generate_recommendation(
            user_id=current_user.id,
            farm_id=farm_id,
        )
    except FarmNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )
    except RecommendationConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except RecommendationResponseParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except RecommendationProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except RecommendationContextError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except (FarmPersistenceError, RecommendationPersistenceError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate farm recommendations",
        )
