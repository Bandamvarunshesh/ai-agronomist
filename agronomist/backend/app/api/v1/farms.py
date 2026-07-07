from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import get_current_farmer, get_farm_service
from app.models.user import User
from app.schemas.farm import FarmCreate, FarmRead, FarmUpdate
from app.services.exceptions import FarmNotFoundError, FarmPersistenceError
from app.services.farm_service import FarmService


router = APIRouter(prefix="/farms", tags=["farms"])


def farm_not_found_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Farm not found",
    )


def farm_persistence_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to persist farm changes",
    )


@router.post("", response_model=FarmRead, status_code=status.HTTP_201_CREATED)
def create_farm(
    farm_in: FarmCreate,
    current_user: User = Depends(get_current_farmer),
    farm_service: FarmService = Depends(get_farm_service),
) -> FarmRead:
    try:
        return farm_service.create_farm(current_user.id, farm_in)
    except FarmPersistenceError:
        raise farm_persistence_error()


@router.get("", response_model=list[FarmRead])
def list_farms(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_farmer),
    farm_service: FarmService = Depends(get_farm_service),
) -> list[FarmRead]:
    try:
        return list(farm_service.list_farms(current_user.id, skip=skip, limit=limit))
    except FarmPersistenceError:
        raise farm_persistence_error()


@router.get("/{farm_id}", response_model=FarmRead)
def get_farm(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    farm_service: FarmService = Depends(get_farm_service),
) -> FarmRead:
    try:
        return farm_service.get_farm(current_user.id, farm_id)
    except FarmNotFoundError:
        raise farm_not_found_error()
    except FarmPersistenceError:
        raise farm_persistence_error()


@router.put("/{farm_id}", response_model=FarmRead)
def update_farm(
    farm_id: uuid.UUID,
    farm_in: FarmUpdate,
    current_user: User = Depends(get_current_farmer),
    farm_service: FarmService = Depends(get_farm_service),
) -> FarmRead:
    try:
        return farm_service.update_farm(current_user.id, farm_id, farm_in)
    except FarmNotFoundError:
        raise farm_not_found_error()
    except FarmPersistenceError:
        raise farm_persistence_error()


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_farmer),
    farm_service: FarmService = Depends(get_farm_service),
) -> Response:
    try:
        farm_service.delete_farm(current_user.id, farm_id)
    except FarmNotFoundError:
        raise farm_not_found_error()
    except FarmPersistenceError:
        raise farm_persistence_error()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
