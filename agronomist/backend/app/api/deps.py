from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.ai_farming_chat_service import AIFarmingChatService
from app.services.crop_image_service import CropImageService
from app.services.diagnosis_service import DiagnosisService
from app.services.escalation_service import EscalationService
from app.services.farm_service import FarmService
from app.services.farm_intelligence_service import FarmIntelligenceService
from app.services.intelligence_service import IntelligenceService
from app.services.knowledge_service import KnowledgeService
from app.services.notification_service import NotificationService
from app.services.recommendation_engine_service import RecommendationEngineService
from app.services.stage_advisory_service import StageAdvisoryService
from app.services.timeline_service import TimelineService
from app.services.user_service import UserService
from app.services.weather_service import WeatherService


bearer_scheme = HTTPBearer(auto_error=False)


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def inactive_user_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User account is inactive",
    )


def farmer_required_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only farmers can manage farms",
    )


def admin_required_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access is required",
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise authentication_error()

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")
        user_id = uuid.UUID(str(subject))
    except (JWTError, TypeError, ValueError):
        raise authentication_error()

    user = UserService(db).get_by_id(user_id)
    if user is None:
        raise authentication_error()

    if not user.is_active:
        raise inactive_user_error()

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise inactive_user_error()
    return current_user


def get_current_farmer(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != "farmer":
        raise farmer_required_error()
    return current_user


def get_current_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != "admin":
        raise admin_required_error()
    return current_user


def get_farm_service(db: Session = Depends(get_db)) -> FarmService:
    return FarmService(db)


def get_crop_image_service(db: Session = Depends(get_db)) -> CropImageService:
    return CropImageService(db)


def get_diagnosis_service(db: Session = Depends(get_db)) -> DiagnosisService:
    return DiagnosisService(db)


def get_escalation_service(db: Session = Depends(get_db)) -> EscalationService:
    return EscalationService(db)


def get_knowledge_service(db: Session = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(db)


def get_intelligence_service(db: Session = Depends(get_db)) -> IntelligenceService:
    return IntelligenceService(db)


def get_ai_farming_chat_service(
    db: Session = Depends(get_db),
) -> AIFarmingChatService:
    return AIFarmingChatService(db)


def get_weather_service(db: Session = Depends(get_db)) -> WeatherService:
    return WeatherService(db)


def get_farm_intelligence_service(
    db: Session = Depends(get_db),
) -> FarmIntelligenceService:
    return FarmIntelligenceService(db)


def get_stage_advisory_service(
    db: Session = Depends(get_db),
) -> StageAdvisoryService:
    return StageAdvisoryService(db)


def get_timeline_service(db: Session = Depends(get_db)) -> TimelineService:
    return TimelineService(db)


def get_recommendation_engine_service(
    db: Session = Depends(get_db),
) -> RecommendationEngineService:
    return RecommendationEngineService(db)


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(db)
