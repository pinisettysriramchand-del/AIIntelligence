"""KPI request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from stratiq.domain.enums import KPIDomain


class KPIResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    domain: KPIDomain
    name: str
    value: str
    unit: str | None
    period: str | None
    evidence_chunk_ids: list[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    business_meaning: str | None = None
    confidence: float = 0.5
    dimensions: dict[str, Any] = Field(default_factory=dict)
    previous_value: str | None = None
    previous_period: str | None = None
    trend: str = "unknown"
    delta_label: str | None = None

    model_config = {"from_attributes": True}


class KPIListResponse(BaseModel):
    items: list[KPIResponse]
    total: int


class ChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    chunk_index: int
    page_number: int | None
    metadata: dict[str, Any]
