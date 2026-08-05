"""Document request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

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

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
