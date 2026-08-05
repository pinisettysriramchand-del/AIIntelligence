"""Chat router: sessions and messages with RAG."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from stratiq.application.chat import ChatService
from stratiq.domain.exceptions import AuthorizationError, NotFoundError
from stratiq.interface.deps import CurrentUser, get_chat_service
from stratiq.interface.schemas.chat import (
    ChatMessageResponse,
    ChatSessionResponse,
    CitationResponse,
    CreateSessionRequest,
    PostMessageRequest,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    current_user: CurrentUser,
    chat_svc: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    session = await chat_svc.create_session(current_user.id, body.title)
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    current_user: CurrentUser,
    chat_svc: ChatService = Depends(get_chat_service),
) -> list[ChatSessionResponse]:
    sessions = await chat_svc.list_sessions(current_user.id)
    return [
        ChatSessionResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    chat_svc: ChatService = Depends(get_chat_service),
) -> list[ChatMessageResponse]:
    try:
        messages = await chat_svc.list_messages(session_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return [_msg_response(m) for m in messages]


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def post_message(
    session_id: uuid.UUID,
    body: PostMessageRequest,
    current_user: CurrentUser,
    chat_svc: ChatService = Depends(get_chat_service),
) -> ChatMessageResponse:
    try:
        msg = await chat_svc.post_message(session_id, current_user.id, body.content)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return _msg_response(msg)


def _msg_response(msg: object) -> ChatMessageResponse:
    from stratiq.domain.entities import ChatMessage

    assert isinstance(msg, ChatMessage)
    return ChatMessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        content=msg.content,
        citations=[
            CitationResponse(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                excerpt=c.excerpt,
            )
            for c in msg.citations
        ],
        created_at=msg.created_at,
    )
