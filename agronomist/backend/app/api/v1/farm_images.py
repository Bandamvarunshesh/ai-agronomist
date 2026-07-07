from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.deps import get_crop_image_service, get_current_farmer
from app.models.user import User
from app.schemas.crop_image import CropImageRead
from app.services.crop_image_service import CropImageService
from app.services.exceptions import (
    FarmNotFoundError,
    ImagePersistenceError,
    ImageStorageError,
    ImageTooLargeError,
    ImageValidationError,
)


router = APIRouter(prefix="/farms/{farm_id}/images", tags=["farm-images"])


def farm_not_found_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Farm not found",
    )


def image_storage_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to store uploaded image",
    )


def image_persistence_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to persist image metadata",
    )


@router.post("", response_model=CropImageRead, status_code=status.HTTP_201_CREATED)
def upload_crop_image(
    farm_id: uuid.UUID,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_farmer),
    crop_image_service: CropImageService = Depends(get_crop_image_service),
) -> CropImageRead:
    try:
        return crop_image_service.upload_image(
            user_id=current_user.id,
            farm_id=farm_id,
            image=image,
        )
    except FarmNotFoundError:
        raise farm_not_found_error()
    except ImageTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        )
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except ImageStorageError:
        raise image_storage_error()
    except ImagePersistenceError:
        raise image_persistence_error()


@router.get("", response_model=list[CropImageRead])
def list_crop_images(
    farm_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_farmer),
    crop_image_service: CropImageService = Depends(get_crop_image_service),
) -> list[CropImageRead]:
    try:
        return list(
            crop_image_service.list_images(
                user_id=current_user.id,
                farm_id=farm_id,
                skip=skip,
                limit=limit,
            )
        )
    except FarmNotFoundError:
        raise farm_not_found_error()
    except ImagePersistenceError:
        raise image_persistence_error()
