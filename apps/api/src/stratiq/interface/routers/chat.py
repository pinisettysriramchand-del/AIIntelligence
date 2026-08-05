from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from stratiq.domain.entities import User
from stratiq.domain.exceptions import NotFoundError, ValidationError
from stratiq.interface.deps import Services, get_current_user, get_services
from stratiq.interface.schemas.chat import (
    AskRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    CitationResponse,
    CreateSessionRequest,
)

router = APIRouter(prefix="/chat", tags=["chat"])


def _message(msg) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=str(msg.id),
        session_id=str(msg.session_id),
        role=msg.role,
        content=msg.content,
        citations=[
            CitationResponse(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                excerpt=c.excerpt,
                score=c.score,
            )
            for c in msg.citations
        ],
    )


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> ChatSessionResponse:
    session = await services.chat.create_session(user.id, body.title)
    return ChatSessionResponse(id=str(session.id), title=session.title)


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> list[ChatSessionResponse]:
    sessions = await services.chat.list_sessions(user.id)
    return [ChatSessionResponse(id=str(s.id), title=s.title) for s in sessions]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    session_id: UUID,
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> list[ChatMessageResponse]:
    try:
        messages = await services.chat.list_messages(session_id, user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_message(m) for m in messages]


@router.post("", response_model=ChatMessageResponse)
async def ask(
    body: AskRequest,
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> ChatMessageResponse:
    try:
        message = await services.chat.ask(
            owner_id=user.id,
            question=body.question,
            session_id=UUID(body.session_id) if body.session_id else None,
            document_id=UUID(body.document_id) if body.document_id else None,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _message(message)
