from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_farmer, get_farm_intelligence_service
from app.models.user import User
from app.schemas.farm_intelligence import (
    AdvisoryIntelligenceResponseRead,
    FarmIntelligenceRead,
    FarmRiskRead,
    MarketIntelligenceResponseRead,
    NewsIntelligenceResponseRead,
    SoilIntelligenceResponseRead,
)
from app.services.exceptions import FarmNotFoundError, FarmPersistenceError
from app.services.farm_intelligence_service import FarmIntelligenceService


router = APIRouter(prefix="/farms/{farm_id}", tags=["farm-intelligence"])


def farm_not_found_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Farm not found",
    )


def intelligence_error(detail: str = "Unable to fetch farm intelligence") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail,
    )


@router.get("/intelligence", response_model=FarmIntelligenceRead)
def get_farm_intelligence(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    intelligence_service: FarmIntelligenceService = Depends(get_farm_intelligence_service),
) -> FarmIntelligenceRead:
    try:
        return intelligence_service.get_farm_intelligence(
            user_id=current_user.id,
            farm_id=farm_id,
        )
    except FarmNotFoundError:
        raise farm_not_found_error()
    except FarmPersistenceError:
        raise intelligence_error()


@router.get("/market", response_model=MarketIntelligenceResponseRead)
def get_farm_market(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    intelligence_service: FarmIntelligenceService = Depends(get_farm_intelligence_service),
) -> MarketIntelligenceResponseRead:
    try:
        return intelligence_service.get_market_intelligence(
            user_id=current_user.id,
            farm_id=farm_id,
        )
    except FarmNotFoundError:
        raise farm_not_found_error()
    except FarmPersistenceError:
        raise intelligence_error("Unable to fetch farm market intelligence")


@router.get("/advisories", response_model=AdvisoryIntelligenceResponseRead)
def get_farm_advisories(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    intelligence_service: FarmIntelligenceService = Depends(get_farm_intelligence_service),
) -> AdvisoryIntelligenceResponseRead:
    try:
        return intelligence_service.get_advisory_intelligence(
            user_id=current_user.id,
            farm_id=farm_id,
        )
    except FarmNotFoundError:
        raise farm_not_found_error()
    except FarmPersistenceError:
        raise intelligence_error("Unable to fetch farm advisories")


@router.get("/news", response_model=NewsIntelligenceResponseRead)
def get_farm_news(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    intelligence_service: FarmIntelligenceService = Depends(get_farm_intelligence_service),
) -> NewsIntelligenceResponseRead:
    try:
        return intelligence_service.get_news_intelligence(
            user_id=current_user.id,
            farm_id=farm_id,
        )
    except FarmNotFoundError:
        raise farm_not_found_error()
    except FarmPersistenceError:
        raise intelligence_error("Unable to fetch farm news")


@router.get("/soil", response_model=SoilIntelligenceResponseRead)
def get_farm_soil(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    intelligence_service: FarmIntelligenceService = Depends(get_farm_intelligence_service),
) -> SoilIntelligenceResponseRead:
    try:
        return intelligence_service.get_soil_intelligence(
            user_id=current_user.id,
            farm_id=farm_id,
        )
    except FarmNotFoundError:
        raise farm_not_found_error()
    except FarmPersistenceError:
        raise intelligence_error("Unable to fetch farm soil intelligence")


@router.get("/risk", response_model=FarmRiskRead)
def get_farm_risk(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    intelligence_service: FarmIntelligenceService = Depends(get_farm_intelligence_service),
) -> FarmRiskRead:
    try:
        return intelligence_service.get_risk_intelligence(
            user_id=current_user.id,
            farm_id=farm_id,
        )
    except FarmNotFoundError:
        raise farm_not_found_error()
    except FarmPersistenceError:
        raise intelligence_error("Unable to fetch farm risk intelligence")
