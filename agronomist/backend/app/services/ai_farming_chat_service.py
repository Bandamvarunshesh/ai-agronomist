from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import ChatMessage, ChatSession
from app.models.crop import Diagnosis
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatMessageCreate, ChatSessionCreate
from app.services.exceptions import (
    ChatConfigurationError,
    ChatPersistenceError,
    ChatProviderError,
    ChatSessionNotFoundError,
    FarmNotFoundError,
    FarmPersistenceError,
)
from app.services.farm_aware_prompt_builder import FarmAwarePromptBuilder
from app.services.farm_service import FarmService
from app.services.knowledge_service import KnowledgeService
from app.services.timeline_service import TimelineService


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatMessageExchange:
    user_message: ChatMessage
    assistant_message: ChatMessage


class AIFarmingChatService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ChatRepository(db)
        self.farm_service = FarmService(db)
        self.knowledge_service = KnowledgeService(db)
        self.prompt_builder = FarmAwarePromptBuilder()
        self.timeline_service = TimelineService(db)

    def create_session(
        self,
        *,
        user_id: uuid.UUID,
        session_in: ChatSessionCreate,
    ) -> ChatSession:
        if session_in.farm_id is not None:
            self._ensure_farm_owner(user_id, session_in.farm_id)

        chat_session = ChatSession(
            user_id=user_id,
            farm_id=session_in.farm_id,
            title=session_in.title,
            channel=session_in.channel,
            session_metadata={"rag_enabled": True},
        )
        self.repository.add_session(chat_session)
        try:
            self.db.flush()
            if chat_session.farm_id is not None:
                self.timeline_service.add_event(
                    farm_id=chat_session.farm_id,
                    user_id=user_id,
                    event_type="chat_session",
                    title="Farming chat session started",
                    description=chat_session.title,
                    source="chat",
                    payload={
                        "chat_session_id": str(chat_session.id),
                        "title": chat_session.title,
                        "channel": chat_session.channel,
                    },
                )
            self.db.commit()
            self.db.refresh(chat_session)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise ChatPersistenceError from exc

        return chat_session

    def list_messages(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ChatMessage]:
        self._get_session(user_id=user_id, session_id=session_id)
        try:
            return self.repository.list_messages_for_session(
                session_id,
                skip=skip,
                limit=limit,
            )
        except SQLAlchemyError as exc:
            raise ChatPersistenceError from exc

    def send_message(
        self,
        *,
        user: User,
        session_id: uuid.UUID,
        message_in: ChatMessageCreate,
    ) -> ChatMessageExchange:
        chat_session = self._get_session(user_id=user.id, session_id=session_id)
        history = self._get_recent_messages(chat_session.id)
        recent_diagnoses = self._get_recent_diagnoses(
            user_id=user.id,
            farm_id=chat_session.farm_id,
        )
        rag_context, citations = self._get_rag_context(
            farm=chat_session.farm,
            user_content=message_in.content,
        )
        system_instruction = self.prompt_builder.build_system_instruction(
            user=user,
            farm=chat_session.farm,
            recent_diagnoses=recent_diagnoses,
            rag_context=rag_context,
        )

        assistant_content = self._generate_assistant_response(
            system_instruction=system_instruction,
            history=history,
            user_content=message_in.content,
        )

        user_message = ChatMessage(
            session_id=chat_session.id,
            user_id=user.id,
            role="user",
            content=message_in.content,
            sent_at=datetime.now(timezone.utc),
            message_metadata={"source": "api"},
        )
        assistant_message = ChatMessage(
            session_id=chat_session.id,
            user_id=None,
            role="assistant",
            content=assistant_content,
            sent_at=datetime.now(timezone.utc),
            message_metadata={
                "provider": "gemini",
                "model": settings.gemini_model,
                "rag_context_used": bool(rag_context),
                "citations": citations,
                "farm_id": str(chat_session.farm_id) if chat_session.farm_id else None,
                "recent_diagnosis_ids": [
                    str(diagnosis.id) for diagnosis in recent_diagnoses
                ],
            },
        )

        if chat_session.title is None:
            chat_session.title = self._build_session_title(message_in.content)

        self.repository.add_message(user_message)
        self.repository.add_message(assistant_message)
        try:
            self.db.commit()
            self.db.refresh(user_message)
            self.db.refresh(assistant_message)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise ChatPersistenceError from exc

        return ChatMessageExchange(
            user_message=user_message,
            assistant_message=assistant_message,
        )

    def _ensure_farm_owner(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> None:
        try:
            self.farm_service.get_farm(user_id, farm_id)
        except FarmNotFoundError:
            raise
        except FarmPersistenceError as exc:
            raise ChatPersistenceError from exc

    def _get_session(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ChatSession:
        try:
            chat_session = self.repository.get_session_for_user(session_id, user_id)
        except SQLAlchemyError as exc:
            raise ChatPersistenceError from exc

        if chat_session is None:
            raise ChatSessionNotFoundError
        return chat_session

    def _get_recent_messages(self, session_id: uuid.UUID) -> Sequence[ChatMessage]:
        try:
            return self.repository.list_recent_messages_for_session(session_id)
        except SQLAlchemyError as exc:
            raise ChatPersistenceError from exc

    def _get_recent_diagnoses(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID | None,
    ) -> Sequence[Diagnosis]:
        try:
            return self.repository.list_recent_diagnoses_for_user(
                user_id,
                farm_id=farm_id,
            )
        except SQLAlchemyError as exc:
            raise ChatPersistenceError from exc

    def _get_rag_context(
        self,
        *,
        farm,
        user_content: str,
    ) -> tuple[str, list[dict[str, Any]]]:
        query_parts = [user_content]
        if farm is not None:
            query_parts.extend([farm.crop, farm.district, farm.state])
        query = " ".join(part for part in query_parts if part)
        return self.knowledge_service.build_rag_context(query=query, limit=5)

    def _generate_assistant_response(
        self,
        *,
        system_instruction: str,
        history: Sequence[ChatMessage],
        user_content: str,
    ) -> str:
        self._validate_configuration()
        contents = self._build_gemini_contents(history, user_content)

        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.35,
                    system_instruction=system_instruction,
                ),
            )
            return self._extract_response_text(response)
        except ChatProviderError:
            raise
        except Exception as exc:
            logger.exception(
                "Gemini farming chat request failed: model=%s error=%s",
                settings.gemini_model,
                str(exc),
            )
            raise ChatProviderError("Gemini farming chat request failed") from exc

    def _validate_configuration(self) -> None:
        if not settings.gemini_api_key.strip():
            raise ChatConfigurationError("GEMINI_API_KEY is not configured")

    def _build_gemini_contents(
        self,
        history: Sequence[ChatMessage],
        user_content: str,
    ) -> list[Any]:
        contents: list[Any] = []
        for message in history:
            if message.role not in {"user", "assistant"}:
                continue
            role = "model" if message.role == "assistant" else "user"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=message.content)],
                )
            )

        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_content)],
            )
        )
        return contents

    def _extract_response_text(self, response: Any) -> str:
        response_text = getattr(response, "output_text", None) or getattr(
            response,
            "text",
            "",
        )
        if not isinstance(response_text, str) or not response_text.strip():
            raise ChatProviderError("Gemini returned an empty farming chat response")
        return response_text.strip()

    def _build_session_title(self, content: str) -> str:
        title = " ".join(content.split())
        if len(title) > 80:
            title = f"{title[:77].rstrip()}..."
        return title or "Farming chat"

    def _commit_and_refresh(self, chat_session: ChatSession) -> ChatSession:
        try:
            self.db.commit()
            self.db.refresh(chat_session)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise ChatPersistenceError from exc
        return chat_session
