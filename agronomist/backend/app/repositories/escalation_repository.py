from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.chat import ChatSession
from app.models.crop import Diagnosis
from app.models.escalation import Escalation, EscalationContact


class EscalationRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_contact(self, contact: EscalationContact) -> EscalationContact:
        self.db.add(contact)
        return contact

    def add_escalation(self, escalation: Escalation) -> Escalation:
        self.db.add(escalation)
        return escalation

    def get_contact(self, contact_id: uuid.UUID) -> EscalationContact | None:
        statement = select(EscalationContact).where(EscalationContact.id == contact_id)
        return self.db.execute(statement).scalar_one_or_none()

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
        statement = select(EscalationContact)
        if is_active is not None:
            statement = statement.where(EscalationContact.is_active.is_(is_active))
        if contact_type is not None:
            statement = statement.where(EscalationContact.contact_type == contact_type)
        if state is not None:
            statement = statement.where(
                func.lower(EscalationContact.state) == state.lower(),
            )
        if district is not None:
            statement = statement.where(
                func.lower(EscalationContact.district) == district.lower(),
            )

        statement = (
            statement.order_by(
                EscalationContact.contact_priority.asc(),
                EscalationContact.created_at.asc(),
            )
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def find_exact_contact(
        self,
        *,
        state: str,
        district: str,
        contact_type: str | None = None,
    ) -> EscalationContact | None:
        statement = self._active_contact_statement(contact_type=contact_type).where(
            func.lower(EscalationContact.state) == state.lower(),
            func.lower(EscalationContact.district) == district.lower(),
        )
        return self.db.execute(statement).scalars().first()

    def find_state_contact(
        self,
        *,
        state: str,
        contact_type: str | None = None,
    ) -> EscalationContact | None:
        statement = self._active_contact_statement(contact_type=contact_type).where(
            func.lower(EscalationContact.state) == state.lower(),
            or_(
                EscalationContact.district.is_(None),
                EscalationContact.district == "",
                EscalationContact.is_fallback.is_(True),
            ),
        )
        return self.db.execute(statement).scalars().first()

    def find_fallback_contact(
        self,
        *,
        state: str | None = None,
        contact_type: str | None = None,
    ) -> EscalationContact | None:
        statement = self._active_contact_statement(contact_type=contact_type).where(
            EscalationContact.is_fallback.is_(True),
        )
        if state is not None:
            statement = statement.where(
                or_(
                    func.lower(EscalationContact.state) == state.lower(),
                    EscalationContact.state.is_(None),
                    EscalationContact.state == "",
                )
            )
        return self.db.execute(statement).scalars().first()

    def list_escalations_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Escalation]:
        statement = (
            select(Escalation)
            .options(joinedload(Escalation.contact))
            .where(Escalation.user_id == user_id)
            .order_by(Escalation.escalated_at.desc(), Escalation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def list_escalations(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Escalation]:
        statement = (
            select(Escalation)
            .options(joinedload(Escalation.contact))
            .order_by(Escalation.escalated_at.desc(), Escalation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def get_diagnosis_for_farm_user(
        self,
        *,
        diagnosis_id: uuid.UUID,
        farm_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Diagnosis | None:
        statement = select(Diagnosis).where(
            Diagnosis.id == diagnosis_id,
            Diagnosis.farm_id == farm_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_chat_session_for_farm_user(
        self,
        *,
        chat_session_id: uuid.UUID,
        farm_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ChatSession | None:
        statement = select(ChatSession).where(
            ChatSession.id == chat_session_id,
            ChatSession.farm_id == farm_id,
            ChatSession.user_id == user_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def _active_contact_statement(
        self,
        *,
        contact_type: str | None,
    ):
        statement = (
            select(EscalationContact)
            .where(EscalationContact.is_active.is_(True))
            .order_by(
                EscalationContact.contact_priority.asc(),
                EscalationContact.created_at.asc(),
            )
        )
        if contact_type is not None:
            statement = statement.where(EscalationContact.contact_type == contact_type)
        return statement
