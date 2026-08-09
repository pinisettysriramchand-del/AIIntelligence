"""Document request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from typing import Any

from pydantic import BaseModel, Field

from stratiq.domain.enums import DocumentStatus


class DocumentResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    quality_warnings: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class ProcessingJobResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    owner_id: uuid.UUID
    status: str
    attempt: int
    max_attempts: int
    idempotency_key: str
    arq_job_id: str | None = None
    error_message: str | None = None
    correlation_id: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ProcessingJobListResponse(BaseModel):
    items: list[ProcessingJobResponse]
    total: int
