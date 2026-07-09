from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.chat import ChatMessage, ChatSession
from app.models.crop import Diagnosis
from app.models.farm import Farm


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_session(self, session: ChatSession) -> ChatSession:
        self.db.add(session)
        return session

    def add_message(self, message: ChatMessage) -> ChatMessage:
        self.db.add(message)
        return message

    def get_session_for_user(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ChatSession | None:
        statement = (
            select(ChatSession)
            .options(joinedload(ChatSession.farm))
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        return self.db.execute(statement).scalar_one_or_none()

    def list_messages_for_session(
        self,
        session_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.sent_at.asc(), ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def list_recent_messages_for_session(
        self,
        session_id: uuid.UUID,
        *,
        limit: int = 12,
    ) -> Sequence[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.sent_at.desc(), ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = self.db.execute(statement).scalars().all()
        return list(reversed(messages))

    def list_recent_messages_for_farm(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        limit: int = 12,
    ) -> Sequence[ChatMessage]:
        statement = (
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.farm_id == farm_id,
                ChatMessage.role.in_(["user", "assistant"]),
            )
            .order_by(ChatMessage.sent_at.desc(), ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = self.db.execute(statement).scalars().all()
        return list(reversed(messages))

    def list_recent_diagnoses_for_user(
        self,
        user_id: uuid.UUID,
        *,
        farm_id: uuid.UUID | None = None,
        limit: int = 3,
    ) -> Sequence[Diagnosis]:
        statement = (
            select(Diagnosis)
            .join(Farm, Diagnosis.farm_id == Farm.id)
            .where(Farm.user_id == user_id)
            .order_by(Diagnosis.created_at.desc())
            .limit(limit)
        )
        if farm_id is not None:
            statement = statement.where(Diagnosis.farm_id == farm_id)

        return self.db.execute(statement).scalars().all()
