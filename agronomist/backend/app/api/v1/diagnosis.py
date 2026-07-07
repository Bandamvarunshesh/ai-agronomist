from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.deps import get_current_farmer, get_diagnosis_service
from app.models.user import User
from app.schemas.diagnosis import DiagnosisRead, DiagnosisRequest
from app.services.diagnosis_service import DiagnosisService
from app.services.exceptions import (
    DiagnosisPersistenceError,
    FarmNotFoundError,
    ImageFileNotFoundError,
    ImageNotFoundError,
    VisionConfigurationError,
    VisionProviderError,
    VisionResponseParseError,
)


router = APIRouter(prefix="/farms/{farm_id}/diagnose", tags=["diagnosis"])


@router.post("", response_model=DiagnosisRead, status_code=status.HTTP_201_CREATED)
def diagnose_farm_image(
    farm_id: uuid.UUID,
    diagnosis_in: Optional[DiagnosisRequest] = Body(default=None),
    current_user: User = Depends(get_current_farmer),
    diagnosis_service: DiagnosisService = Depends(get_diagnosis_service),
) -> DiagnosisRead:
    try:
        return diagnosis_service.diagnose_farm_image(
            user_id=current_user.id,
            farm_id=farm_id,
            diagnosis_in=diagnosis_in or DiagnosisRequest(),
        )
    except FarmNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )
    except ImageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found for this farm",
        )
    except ImageFileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Uploaded image file was not found on local storage",
        )
    except VisionConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except VisionResponseParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except VisionProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except DiagnosisPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save diagnosis",
        )
