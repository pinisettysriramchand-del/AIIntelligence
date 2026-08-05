"""Concrete SQLAlchemy repository implementations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from stratiq.domain.entities import (
    AuditEvent,
    ChatMessage,
    ChatSession,
    Chunk,
    Citation,
    Document,
    KPI,
    User,
)
from stratiq.domain.enums import AuditEventType, DocumentStatus, KPIDomain
from stratiq.infrastructure.db.models import (
    AuditEventModel,
    ChatMessageModel,
    ChatSessionModel,
    ChunkModel,
    DocumentModel,
    KPIModel,
    UserModel,
)


def _user_from_model(m: UserModel) -> User:
    return User(
        id=m.id,
        email=m.email,
        hashed_password=m.hashed_password,
        full_name=m.full_name,
        is_active=m.is_active,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _doc_from_model(m: DocumentModel) -> Document:
    return Document(
        id=m.id,
        owner_id=m.owner_id,
        filename=m.filename,
        original_filename=m.original_filename,
        mime_type=m.mime_type,
        size_bytes=m.size_bytes,
        storage_path=m.storage_path,
        status=DocumentStatus(m.status),
        error_message=m.error_message,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _chunk_from_model(m: ChunkModel) -> Chunk:
    return Chunk(
        id=m.id,
        document_id=m.document_id,
        content=m.content,
        chunk_index=m.chunk_index,
        page_number=m.page_number,
        metadata=m.metadata_,
        created_at=m.created_at,
    )


def _kpi_from_model(m: KPIModel) -> KPI:
    evidence_ids = [uuid.UUID(cid) if isinstance(cid, str) else cid for cid in m.evidence_chunk_ids]
    return KPI(
        id=m.id,
        document_id=m.document_id,
        owner_id=m.owner_id,
        domain=KPIDomain(m.domain),
        name=m.name,
        value=m.value,
        unit=m.unit,
        period=m.period,
        evidence_chunk_ids=evidence_ids,
        raw_extraction=m.raw_extraction,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _session_from_model(m: ChatSessionModel) -> ChatSession:
    return ChatSession(
        id=m.id,
        owner_id=m.owner_id,
        title=m.title,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _message_from_model(m: ChatMessageModel) -> ChatMessage:
    citations = [
        Citation(
            chunk_id=uuid.UUID(c["chunk_id"]),
            document_id=uuid.UUID(c["document_id"]),
            excerpt=c["excerpt"],
        )
        for c in (m.citations or [])
    ]
    return ChatMessage(
        id=m.id,
        session_id=m.session_id,
        role=m.role,
        content=m.content,
        citations=citations,
        created_at=m.created_at,
    )


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user: User) -> None:
        model = UserModel(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return _user_from_model(model) if model else None


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, doc: Document) -> None:
        model = DocumentModel(
            id=doc.id,
            owner_id=doc.owner_id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            storage_path=doc.storage_path,
            status=doc.status.value,
            error_message=doc.error_message,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, doc_id: uuid.UUID) -> Document | None:
        result = await self._session.execute(select(DocumentModel).where(DocumentModel.id == doc_id))
        model = result.scalar_one_or_none()
        return _doc_from_model(model) if model else None

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[Document]:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.owner_id == owner_id).order_by(DocumentModel.created_at.desc())
        )
        return [_doc_from_model(m) for m in result.scalars().all()]

    async def update_status(
        self,
        doc_id: uuid.UUID,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> None:
        values: dict[str, Any] = {"status": status.value, "updated_at": datetime.now(UTC)}
        if error_message is not None:
            values["error_message"] = error_message
        await self._session.execute(update(DocumentModel).where(DocumentModel.id == doc_id).values(**values))
        await self._session.flush()

    async def delete(self, doc_id: uuid.UUID) -> None:
        await self._session.execute(delete(DocumentModel).where(DocumentModel.id == doc_id))
        await self._session.flush()


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, chunks: list[Chunk]) -> None:
        models = [
            ChunkModel(
                id=c.id,
                document_id=c.document_id,
                content=c.content,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                metadata_=c.metadata,
                created_at=c.created_at,
            )
            for c in chunks
        ]
        self._session.add_all(models)
        await self._session.flush()

    async def get_by_ids(self, chunk_ids: list[uuid.UUID]) -> list[Chunk]:
        result = await self._session.execute(select(ChunkModel).where(ChunkModel.id.in_(chunk_ids)))
        return [_chunk_from_model(m) for m in result.scalars().all()]

    async def list_by_document(self, document_id: uuid.UUID) -> list[Chunk]:
        result = await self._session.execute(
            select(ChunkModel).where(ChunkModel.document_id == document_id).order_by(ChunkModel.chunk_index)
        )
        return [_chunk_from_model(m) for m in result.scalars().all()]


class KPIRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, kpis: list[KPI]) -> None:
        models = [
            KPIModel(
                id=k.id,
                document_id=k.document_id,
                owner_id=k.owner_id,
                domain=k.domain.value,
                name=k.name,
                value=k.value,
                unit=k.unit,
                period=k.period,
                evidence_chunk_ids=[str(cid) for cid in k.evidence_chunk_ids],
                raw_extraction=k.raw_extraction,
                created_at=k.created_at,
                updated_at=k.updated_at,
            )
            for k in kpis
        ]
        self._session.add_all(models)
        await self._session.flush()

    async def get_by_id(self, kpi_id: uuid.UUID) -> KPI | None:
        result = await self._session.execute(select(KPIModel).where(KPIModel.id == kpi_id))
        model = result.scalar_one_or_none()
        return _kpi_from_model(model) if model else None

    async def list_by_owner(
        self,
        owner_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        domain: KPIDomain | None = None,
    ) -> list[KPI]:
        stmt = select(KPIModel).where(KPIModel.owner_id == owner_id)
        if document_id is not None:
            stmt = stmt.where(KPIModel.document_id == document_id)
        if domain is not None:
            stmt = stmt.where(KPIModel.domain == domain.value)
        stmt = stmt.order_by(KPIModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [_kpi_from_model(m) for m in result.scalars().all()]


class ChatSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, session_entity: ChatSession) -> None:
        model = ChatSessionModel(
            id=session_entity.id,
            owner_id=session_entity.owner_id,
            title=session_entity.title,
            created_at=session_entity.created_at,
            updated_at=session_entity.updated_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, session_id: uuid.UUID) -> ChatSession | None:
        result = await self._session.execute(select(ChatSessionModel).where(ChatSessionModel.id == session_id))
        model = result.scalar_one_or_none()
        return _session_from_model(model) if model else None

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[ChatSession]:
        result = await self._session.execute(
            select(ChatSessionModel)
            .where(ChatSessionModel.owner_id == owner_id)
            .order_by(ChatSessionModel.updated_at.desc())
        )
        return [_session_from_model(m) for m in result.scalars().all()]


class ChatMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, message: ChatMessage) -> None:
        citations_data = [
            {"chunk_id": str(c.chunk_id), "document_id": str(c.document_id), "excerpt": c.excerpt}
            for c in message.citations
        ]
        model = ChatMessageModel(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            citations=citations_data,
            created_at=message.created_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def list_by_session(self, session_id: uuid.UUID) -> list[ChatMessage]:
        result = await self._session.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at)
        )
        return [_message_from_model(m) for m in result.scalars().all()]


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: AuditEvent) -> None:
        model = AuditEventModel(
            id=event.id,
            user_id=event.user_id,
            event_type=event.event_type.value,
            payload=event.payload,
            ip_address=event.ip_address,
            created_at=event.created_at,
        )
        self._session.add(model)
        await self._session.flush()
