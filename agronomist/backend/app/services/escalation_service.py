from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.crop import Diagnosis
from app.models.escalation import Escalation, EscalationContact
from app.models.farm import Farm
from app.repositories.escalation_repository import EscalationRepository
from app.schemas.escalation import (
    ESCALATION_CONTACT_TYPES,
    EscalationContactCreate,
    EscalationContactUpdate,
    EscalationCreate,
)
from app.services.exceptions import (
    EscalationContactNotFoundError,
    EscalationContactPersistenceError,
    EscalationPersistenceError,
    EscalationValidationError,
    FarmNotFoundError,
    FarmPersistenceError,
    TimelinePersistenceError,
)
from app.services.farm_service import FarmService
from app.services.timeline_service import TimelineService


logger = logging.getLogger(__name__)

HIGH_RISK_DIAGNOSIS_SEVERITIES = {"high", "severe", "critical"}


@dataclass(frozen=True)
class ContactRoute:
    contact: EscalationContact | None
    routing_level: str
    fallback_used: bool
    routing_reason: str


class EscalationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = EscalationRepository(db)
        self.farm_service = FarmService(db)
        self.timeline_service = TimelineService(db)

    def lookup_farm_contact(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        contact_type: str | None = None,
    ) -> tuple[Farm, ContactRoute]:
        self._validate_contact_type(contact_type)
        farm = self._get_farm(user_id=user_id, farm_id=farm_id)
        route = self._route_contact(farm=farm, contact_type=contact_type)
        if route.contact is None:
            raise EscalationContactNotFoundError
        return farm, route

    def list_escalations(
        self,
        *,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Escalation]:
        try:
            return self.repository.list_escalations_by_user(
                user_id,
                skip=skip,
                limit=limit,
            )
        except SQLAlchemyError as exc:
            raise EscalationPersistenceError from exc

    def list_all_escalations(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Escalation]:
        try:
            return self.repository.list_escalations(skip=skip, limit=limit)
        except SQLAlchemyError as exc:
            raise EscalationPersistenceError from exc

    def create_escalation(
        self,
        *,
        user_id: uuid.UUID,
        escalation_in: EscalationCreate,
    ) -> Escalation:
        farm = self._get_farm(user_id=user_id, farm_id=escalation_in.farm_id)
        escalation_type = self._infer_escalation_type(escalation_in)
        diagnosis = self._validate_diagnosis(
            user_id=user_id,
            farm_id=farm.id,
            diagnosis_id=escalation_in.diagnosis_id,
        )
        self._validate_chat_session(
            user_id=user_id,
            farm_id=farm.id,
            chat_session_id=escalation_in.chat_session_id,
        )
        contact_type = escalation_in.contact_type_requested
        if contact_type is None and escalation_type == "diagnosis":
            contact_type = "agronomist"

        try:
            escalation = self._build_escalation(
                user_id=user_id,
                farm=farm,
                escalation_type=escalation_type,
                subject=escalation_in.subject,
                description=escalation_in.description,
                priority=escalation_in.priority,
                diagnosis=diagnosis,
                diagnosis_id=escalation_in.diagnosis_id,
                chat_session_id=escalation_in.chat_session_id,
                contact_type=contact_type,
                metadata={"source": "api"},
            )
            self.db.commit()
            self.db.refresh(escalation)
        except (
            SQLAlchemyError,
            EscalationContactPersistenceError,
            EscalationPersistenceError,
        ) as exc:
            self.db.rollback()
            raise EscalationPersistenceError from exc
        return escalation

    def create_for_diagnosis_if_needed(
        self,
        *,
        user_id: uuid.UUID,
        farm: Farm,
        diagnosis: Diagnosis,
    ) -> Escalation | None:
        severity = diagnosis.severity.lower()
        if not diagnosis.escalate_to_human and severity not in HIGH_RISK_DIAGNOSIS_SEVERITIES:
            return None

        priority = "urgent" if severity in {"severe", "critical"} else "high"
        return self._build_escalation(
            user_id=user_id,
            farm=farm,
            escalation_type="diagnosis",
            subject=f"Diagnosis escalation: {diagnosis.disease_name}",
            description=(
                f"{diagnosis.severity} severity diagnosis with "
                f"{diagnosis.confidence_score} confidence."
            ),
            priority=priority,
            diagnosis=diagnosis,
            diagnosis_id=diagnosis.id,
            chat_session_id=None,
            contact_type="agronomist",
            metadata={"source": "diagnosis", "automatic": True},
        )

    def create_contact(
        self,
        *,
        contact_in: EscalationContactCreate,
    ) -> EscalationContact:
        contact = EscalationContact(
            user_id=None,
            farm_id=None,
            **contact_in.model_dump(),
        )
        self.repository.add_contact(contact)
        return self._commit_and_refresh_contact(contact)

    def list_contacts(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
        contact_type: str | None = None,
        state: str | None = None,
        district: str | None = None,
    ) -> Sequence[EscalationContact]:
        self._validate_contact_type(contact_type)
        try:
            return self.repository.list_contacts(
                skip=skip,
                limit=limit,
                is_active=is_active,
                contact_type=contact_type,
                state=state,
                district=district,
            )
        except SQLAlchemyError as exc:
            raise EscalationContactPersistenceError from exc

    def update_contact(
        self,
        *,
        contact_id: uuid.UUID,
        contact_in: EscalationContactUpdate,
    ) -> EscalationContact:
        try:
            contact = self.repository.get_contact(contact_id)
        except SQLAlchemyError as exc:
            raise EscalationContactPersistenceError from exc

        if contact is None:
            raise EscalationContactNotFoundError

        update_data = contact_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(contact, field, value)

        if not contact.phone_number and not contact.email:
            raise EscalationValidationError(
                "At least one of phone_number or email is required",
            )
        return self._commit_and_refresh_contact(contact)

    def _build_escalation(
        self,
        *,
        user_id: uuid.UUID,
        farm: Farm,
        escalation_type: str,
        subject: str,
        description: str | None,
        priority: str,
        diagnosis: Diagnosis | None = None,
        diagnosis_id: uuid.UUID | None,
        chat_session_id: uuid.UUID | None,
        contact_type: str | None,
        metadata: dict[str, Any],
    ) -> Escalation:
        route = self._route_contact(farm=farm, contact_type=contact_type)
        contact = route.contact
        escalation = Escalation(
            farm_id=farm.id,
            user_id=user_id,
            diagnosis_id=diagnosis_id,
            chat_session_id=chat_session_id,
            contact_id=contact.id if contact is not None else None,
            escalation_type=escalation_type,
            contact_type_requested=contact_type,
            status="routed" if contact is not None else "open",
            priority=priority,
            subject=subject,
            description=description,
            routing_status=route.routing_level,
            routing_reason=route.routing_reason,
            fallback_used=route.fallback_used,
            contact_snapshot=self._contact_snapshot(contact),
            escalation_metadata={
                **metadata,
                "farm_name": farm.farm_name,
                "district": farm.district,
                "state": farm.state,
                "diagnosis_name": diagnosis.disease_name if diagnosis is not None else None,
            },
        )
        self.repository.add_escalation(escalation)
        try:
            self.db.flush()
            self._log_timeline_event(
                user_id=user_id,
                farm=farm,
                escalation=escalation,
                route=route,
            )
        except (SQLAlchemyError, TimelinePersistenceError) as exc:
            raise EscalationPersistenceError from exc

        logger.info(
            "Escalation logged: id=%s farm_id=%s type=%s routing=%s contact_id=%s",
            escalation.id,
            farm.id,
            escalation_type,
            route.routing_level,
            escalation.contact_id,
        )
        return escalation

    def _route_contact(
        self,
        *,
        farm: Farm,
        contact_type: str | None,
    ) -> ContactRoute:
        try:
            exact_contact = self.repository.find_exact_contact(
                state=farm.state,
                district=farm.district,
                contact_type=contact_type,
            )
            if exact_contact is not None:
                return ContactRoute(
                    contact=exact_contact,
                    routing_level="district_contact",
                    fallback_used=False,
                    routing_reason="Matched active contact for farm district and state",
                )

            state_contact = self.repository.find_state_contact(
                state=farm.state,
                contact_type=contact_type,
            )
            if state_contact is not None:
                return ContactRoute(
                    contact=state_contact,
                    routing_level="state_contact",
                    fallback_used=True,
                    routing_reason="District contact missing; routed to state contact",
                )

            fallback_contact = self.repository.find_fallback_contact(
                state=farm.state,
                contact_type=contact_type,
            )
            if fallback_contact is not None:
                return ContactRoute(
                    contact=fallback_contact,
                    routing_level="fallback_contact",
                    fallback_used=True,
                    routing_reason="District/state contact missing; routed to fallback contact",
                )
        except SQLAlchemyError as exc:
            raise EscalationContactPersistenceError from exc

        return ContactRoute(
            contact=None,
            routing_level="no_contact_found",
            fallback_used=False,
            routing_reason="No active escalation contact found in database",
        )

    def _validate_diagnosis(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        diagnosis_id: uuid.UUID | None,
    ) -> Diagnosis | None:
        if diagnosis_id is None:
            return None
        try:
            diagnosis = self.repository.get_diagnosis_for_farm_user(
                diagnosis_id=diagnosis_id,
                farm_id=farm_id,
                user_id=user_id,
            )
        except SQLAlchemyError as exc:
            raise EscalationPersistenceError from exc

        if diagnosis is None:
            raise EscalationValidationError(
                "Diagnosis does not belong to this farm",
            )
        return diagnosis

    def _validate_chat_session(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        chat_session_id: uuid.UUID | None,
    ) -> None:
        if chat_session_id is None:
            return
        try:
            chat_session = self.repository.get_chat_session_for_farm_user(
                chat_session_id=chat_session_id,
                farm_id=farm_id,
                user_id=user_id,
            )
        except SQLAlchemyError as exc:
            raise EscalationPersistenceError from exc

        if chat_session is None:
            raise EscalationValidationError(
                "Chat session does not belong to this farm",
            )

    def _infer_escalation_type(self, escalation_in: EscalationCreate) -> str:
        if escalation_in.escalation_type is not None:
            return escalation_in.escalation_type
        if escalation_in.diagnosis_id is not None:
            return "diagnosis"
        if escalation_in.chat_session_id is not None:
            return "chat"
        return "manual"

    def _validate_contact_type(self, contact_type: str | None) -> None:
        if contact_type is not None and contact_type not in ESCALATION_CONTACT_TYPES:
            raise EscalationValidationError("Unsupported escalation contact type")

    def _get_farm(self, *, user_id: uuid.UUID, farm_id: uuid.UUID) -> Farm:
        try:
            return self.farm_service.get_farm(user_id, farm_id)
        except FarmNotFoundError:
            raise
        except FarmPersistenceError:
            raise
        except SQLAlchemyError as exc:
            raise FarmPersistenceError from exc

    def _log_timeline_event(
        self,
        *,
        user_id: uuid.UUID,
        farm: Farm,
        escalation: Escalation,
        route: ContactRoute,
    ) -> None:
        self.timeline_service.add_event(
            farm_id=farm.id,
            user_id=user_id,
            event_type="escalation",
            title=f"Escalation: {escalation.subject}",
            description=escalation.description,
            source="escalation",
            payload={
                "escalation_id": str(escalation.id),
                "escalation_type": escalation.escalation_type,
                "priority": escalation.priority,
                "status": escalation.status,
                "routing_status": route.routing_level,
                "fallback_used": route.fallback_used,
                "contact_id": str(escalation.contact_id)
                if escalation.contact_id is not None
                else None,
            },
        )

    def _contact_snapshot(
        self,
        contact: EscalationContact | None,
    ) -> dict[str, Any]:
        if contact is None:
            return {}

        return {
            "id": str(contact.id),
            "name": contact.name,
            "contact_type": contact.contact_type,
            "role": contact.role,
            "organization": contact.organization,
            "district": contact.district,
            "state": contact.state,
            "phone_number": contact.phone_number,
            "email": contact.email,
            "preferred_channel": contact.preferred_channel,
            "contact_priority": contact.contact_priority,
            "is_fallback": contact.is_fallback,
        }

    def _commit_and_refresh_contact(
        self,
        contact: EscalationContact,
    ) -> EscalationContact:
        try:
            self.db.commit()
            self.db.refresh(contact)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise EscalationContactPersistenceError from exc
        return contact
