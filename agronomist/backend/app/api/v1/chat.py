from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_ai_farming_chat_service, get_current_active_user
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageExchangeRead,
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionRead,
)
from app.services.ai_farming_chat_service import AIFarmingChatService
from app.services.exceptions import (
    ChatConfigurationError,
    ChatPersistenceError,
    ChatProviderError,
    ChatSessionNotFoundError,
    FarmNotFoundError,
)


router = APIRouter(prefix="/chat", tags=["chat"])


def chat_session_not_found_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chat session not found",
    )


@router.post(
    "/sessions",
    response_model=ChatSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_session(
    session_in: ChatSessionCreate,
    current_user: User = Depends(get_current_active_user),
    chat_service: AIFarmingChatService = Depends(get_ai_farming_chat_service),
) -> ChatSessionRead:
    try:
        return chat_service.create_session(
            user_id=current_user.id,
            session_in=session_in,
        )
    except FarmNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )
    except ChatPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create chat session",
        )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageExchangeRead,
    status_code=status.HTTP_201_CREATED,
)
def send_chat_message(
    session_id: uuid.UUID,
    message_in: ChatMessageCreate,
    current_user: User = Depends(get_current_active_user),
    chat_service: AIFarmingChatService = Depends(get_ai_farming_chat_service),
) -> ChatMessageExchangeRead:
    try:
        return chat_service.send_message(
            user=current_user,
            session_id=session_id,
            message_in=message_in,
        )
    except ChatSessionNotFoundError:
        raise chat_session_not_found_error()
    except ChatConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except ChatProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except ChatPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save chat message",
        )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageRead],
)
def list_chat_messages(
    session_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    chat_service: AIFarmingChatService = Depends(get_ai_farming_chat_service),
) -> list[ChatMessageRead]:
    try:
        return list(
            chat_service.list_messages(
                user_id=current_user.id,
                session_id=session_id,
                skip=skip,
                limit=limit,
            )
        )
    except ChatSessionNotFoundError:
        raise chat_session_not_found_error()
    except ChatPersistenceError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch chat messages",
        )
