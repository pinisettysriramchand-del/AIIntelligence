"""Chat request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=512)


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CitationResponse(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    excerpt: str


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    citations: list[CitationResponse]
    created_at: datetime
    evidence_sufficient: bool = True

    model_config = {"from_attributes": True}


class PostMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
