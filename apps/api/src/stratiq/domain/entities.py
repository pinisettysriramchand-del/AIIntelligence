"""Domain entities – pure Python dataclasses with no framework dependencies."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from stratiq.domain.enums import AuditEventType, DocumentStatus, KPIDomain


@dataclass
class User:
    id: uuid.UUID
    email: str
    hashed_password: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class Document:
    id: uuid.UUID
    owner_id: uuid.UUID
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_path: str
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class Chunk:
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    chunk_index: int
    page_number: int | None
    metadata: dict[str, Any]
    created_at: datetime


@dataclass
class KPI:
    id: uuid.UUID
    document_id: uuid.UUID
    owner_id: uuid.UUID
    domain: KPIDomain
    name: str
    value: str
    unit: str | None
    period: str | None
    evidence_chunk_ids: list[uuid.UUID]
    raw_extraction: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.evidence_chunk_ids:
            raise ValueError(f"KPI '{self.name}' must have at least one evidence_chunk_id.")


@dataclass
class ChatSession:
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ChatMessage:
    id: uuid.UUID
    session_id: uuid.UUID
    role: str  # "user" | "assistant"
    content: str
    citations: list[Citation]
    created_at: datetime


@dataclass
class Citation:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    excerpt: str


@dataclass
class AuditEvent:
    id: uuid.UUID
    user_id: uuid.UUID | None
    event_type: AuditEventType
    payload: dict[str, Any]
    ip_address: str | None
    created_at: datetime
