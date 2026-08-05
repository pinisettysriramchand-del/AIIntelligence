from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    password_hash: str
    full_name: str
    created_at: datetime


@dataclass(slots=True)
class Document:
    id: UUID
    owner_id: UUID
    filename: str
    content_type: str
    storage_key: str
    status: str
    document_type: str
    domain: str | None = None
    domain_confidence: float | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class Chunk:
    id: UUID
    document_id: UUID
    ordinal: int
    content: str
    token_estimate: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class KPI:
    id: UUID
    document_id: UUID
    owner_id: UUID
    name: str
    value: str
    unit: str | None
    period: str | None
    evidence_chunk_ids: list[str]
    domain: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Citation:
    chunk_id: str
    document_id: str
    excerpt: str
    score: float | None = None


@dataclass(slots=True)
class ChatMessage:
    id: UUID
    session_id: UUID
    role: str
    content: str
    citations: list[Citation] = field(default_factory=list)
    created_at: datetime | None = None


@dataclass(slots=True)
class ChatSession:
    id: UUID
    owner_id: UUID
    title: str
    created_at: datetime | None = None


@dataclass(slots=True)
class DecisionCard:
    id: UUID
    owner_id: UUID
    kpi_id: UUID
    document_id: UUID
    kpi_name: str
    current_value: str
    unit: str | None
    period: str | None
    domain: str | None
    trend: str
    health: str
    what_happened: str
    why_it_happened: str
    risks: list[str]
    opportunities: list[str]
    recommendation: str
    forecast_value: str | None
    forecast_horizon: str | None
    forecast_explanation: str | None
    evidence_chunk_ids: list[str]
    related_kpi_ids: list[str] = field(default_factory=list)
    created_at: datetime | None = None


@dataclass(slots=True)
class ExecutiveReport:
    id: UUID
    owner_id: UUID
    summary: str
    health_score: int
    health_label: str
    timeline: list[dict[str, Any]]
    document_id: UUID | None = None
    created_at: datetime | None = None
