"""Domain entities – pure Python dataclasses with no framework dependencies."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from stratiq.domain.enums import (
    AuditEventType,
    DocumentStatus,
    EvidenceMode,
    HealthLabel,
    KPIDomain,
    ProcessingJobStatus,
    TrendDirection,
)


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
    quality_warnings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ProcessingJob:
    id: uuid.UUID
    document_id: uuid.UUID
    owner_id: uuid.UUID
    status: ProcessingJobStatus
    attempt: int
    max_attempts: int
    idempotency_key: str
    arq_job_id: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    correlation_id: str | None = None


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
    business_meaning: str | None = None
    confidence: float = 0.5
    dimensions: dict[str, Any] = field(default_factory=dict)
    previous_value: str | None = None
    previous_period: str | None = None
    trend: TrendDirection = TrendDirection.unknown
    delta_label: str | None = None

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


@dataclass
class DecisionCard:
    id: uuid.UUID
    owner_id: uuid.UUID
    kpi_id: uuid.UUID
    document_id: uuid.UUID
    kpi_name: str
    current_value: str
    unit: str | None
    period: str | None
    domain: str | None
    trend: TrendDirection
    health: HealthLabel
    topic: str
    what_happened: str
    why_it_happened: str
    business_impact: str
    risks: list[str]
    opportunities: list[str]
    recommendation: str
    expected_outcome: str
    forecast_value: str | None
    forecast_horizon: str | None
    forecast_explanation: str | None
    confidence: float
    evidence_mode: EvidenceMode
    evidence_chunk_ids: list[uuid.UUID]
    related_kpi_ids: list[uuid.UUID] = field(default_factory=list)
    created_at: datetime | None = None

    @property
    def kpi_signal(self) -> str:
        """Part 4 §25 KPI signal: value + period + direction + health."""
        unit_part = f" {self.unit}" if self.unit else ""
        period_part = f" ({self.period})" if self.period else ""
        return (
            f"{self.kpi_name}: {self.current_value}{unit_part}{period_part}"
            f" · {self.trend.value} · {self.health.value}"
        )


@dataclass
class ExecutiveReport:
    id: uuid.UUID
    owner_id: uuid.UUID
    summary: str
    health_score: int
    health_label: HealthLabel
    timeline: list[dict[str, Any]]
    document_id: uuid.UUID | None = None
    confidence: float = 0.0
    created_at: datetime | None = None
