"""Audit service – minimal event logging (auth, upload, chat)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from stratiq.domain.enums import AuditEventType


class AuditService:
    def __init__(self, audit_repo: "AuditRepository") -> None:  # noqa: F821
        self._repo = audit_repo

    async def _emit(
        self,
        event_type: AuditEventType,
        user_id: uuid.UUID | None,
        payload: dict[str, Any],
        ip_address: str | None = None,
    ) -> None:
        from stratiq.domain.entities import AuditEvent

        event = AuditEvent(
            id=uuid.uuid4(),
            user_id=user_id,
            event_type=event_type,
            payload=payload,
            ip_address=ip_address,
            created_at=datetime.now(UTC),
        )
        await self._repo.save(event)

    async def log_user_registered(self, user_id: uuid.UUID, email: str, ip: str | None) -> None:
        await self._emit(AuditEventType.user_registered, user_id, {"email": email}, ip)

    async def log_user_login(self, user_id: uuid.UUID, ip: str | None) -> None:
        await self._emit(AuditEventType.user_login, user_id, {}, ip)

    async def log_user_logout(self, user_id: uuid.UUID, ip: str | None) -> None:
        await self._emit(AuditEventType.user_logout, user_id, {}, ip)

    async def log_token_refreshed(self, user_id: uuid.UUID, ip: str | None) -> None:
        await self._emit(AuditEventType.token_refreshed, user_id, {}, ip)

    async def log_document_uploaded(self, user_id: uuid.UUID, doc_id: uuid.UUID, filename: str) -> None:
        await self._emit(AuditEventType.document_uploaded, user_id, {"doc_id": str(doc_id), "filename": filename})

    async def log_document_processed(self, user_id: uuid.UUID, doc_id: uuid.UUID, kpi_count: int) -> None:
        await self._emit(AuditEventType.document_processed, user_id, {"doc_id": str(doc_id), "kpi_count": kpi_count})

    async def log_document_failed(self, user_id: uuid.UUID, doc_id: uuid.UUID, error: str) -> None:
        await self._emit(AuditEventType.document_failed, user_id, {"doc_id": str(doc_id), "error": error})

    async def log_chat_session_created(self, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        await self._emit(AuditEventType.chat_session_created, user_id, {"session_id": str(session_id)})

    async def log_chat_message(self, user_id: uuid.UUID, session_id: uuid.UUID, msg_id: uuid.UUID) -> None:
        await self._emit(
            AuditEventType.chat_message_sent,
            user_id,
            {"session_id": str(session_id), "msg_id": str(msg_id)},
        )
