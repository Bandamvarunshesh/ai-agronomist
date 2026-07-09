from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_current_admin,
    get_current_farmer,
    get_escalation_service,
)
from app.models.user import User
from app.schemas.escalation import (
    EscalationContactCreate,
    EscalationContactLookupRead,
    EscalationContactRead,
    EscalationContactUpdate,
    EscalationCreate,
    EscalationRead,
)
from app.services.escalation_service import EscalationService
from app.services.exceptions import (
    EscalationContactNotFoundError,
    EscalationContactPersistenceError,
    EscalationPersistenceError,
    EscalationValidationError,
    FarmNotFoundError,
    FarmPersistenceError,
)


router = APIRouter(tags=["escalations"])


@router.get(
    "/farms/{farm_id}/escalation-contact",
    response_model=EscalationContactLookupRead,
)
def get_farm_escalation_contact(
    farm_id: uuid.UUID,
    contact_type: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_farmer),
    escalation_service: EscalationService = Depends(get_escalation_service),
) -> EscalationContactLookupRead:
    try:
        farm, route = escalation_service.lookup_farm_contact(
            user_id=current_user.id,
            farm_id=farm_id,
            contact_type=contact_type,
        )
    except FarmNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )
    except EscalationContactNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active escalation contact found",
        )
    except EscalationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except (FarmPersistenceError, EscalationContactPersistenceError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to lookup escalation contact",
        )

    return EscalationContactLookupRead(
        farm_id=farm.id,
        farm_name=farm.farm_name,
        district=farm.district,
        state=farm.state,
        requested_contact_type=contact_type,
        routing_level=route.routing_level,
        fallback_used=route.fallback_used,
        contact=route.contact,
    )


@router.post(
    "/escalations",
    response_model=EscalationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_escalation(
    escalation_in: EscalationCreate,
    current_user: User = Depends(get_current_farmer),
    escalation_service: EscalationService = Depends(get_escalation_service),
) -> EscalationRead:
    try:
        return escalation_service.create_escalation(
            user_id=current_user.id,
            escalation_in=escalation_in,
        )
    except FarmNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )
    except EscalationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except (FarmPersistenceError, EscalationPersistenceError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create escalation",
        )


@router.get("/escalations", response_model=list[EscalationRead])
def get_escalations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_farmer),
    escalation_service: EscalationService = Depends(get_escalation_service),
) -> list[EscalationRead]:
    try:
        return list(
            escalation_service.list_escalations(
                user_id=current_user.id,
                skip=skip,
                limit=limit,
            )
        )
    except EscalationPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch escalations",
        )


@router.post(
    "/admin/escalation-contacts",
    response_model=EscalationContactRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_escalation_contact(
    contact_in: EscalationContactCreate,
    current_user: User = Depends(get_current_admin),
    escalation_service: EscalationService = Depends(get_escalation_service),
) -> EscalationContactRead:
    del current_user
    try:
        return escalation_service.create_contact(contact_in=contact_in)
    except EscalationContactPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create escalation contact",
        )


@router.get(
    "/admin/escalation-contacts",
    response_model=list[EscalationContactRead],
)
def get_admin_escalation_contacts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    is_active: Optional[bool] = Query(default=None),
    contact_type: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_admin),
    escalation_service: EscalationService = Depends(get_escalation_service),
) -> list[EscalationContactRead]:
    del current_user
    try:
        return list(
            escalation_service.list_contacts(
                skip=skip,
                limit=limit,
                is_active=is_active,
                contact_type=contact_type,
                state=state,
                district=district,
            )
        )
    except EscalationContactPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch escalation contacts",
        )
    except EscalationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.put(
    "/admin/escalation-contacts/{contact_id}",
    response_model=EscalationContactRead,
)
def update_admin_escalation_contact(
    contact_id: uuid.UUID,
    contact_in: EscalationContactUpdate,
    current_user: User = Depends(get_current_admin),
    escalation_service: EscalationService = Depends(get_escalation_service),
) -> EscalationContactRead:
    del current_user
    try:
        return escalation_service.update_contact(
            contact_id=contact_id,
            contact_in=contact_in,
        )
    except EscalationContactNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation contact not found",
        )
    except EscalationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except EscalationContactPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update escalation contact",
        )
