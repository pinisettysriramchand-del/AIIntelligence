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
    DecisionCard,
    Document,
    ExecutiveReport,
    KPI,
    ProcessingJob,
    User,
)
from stratiq.domain.enums import (
    AuditEventType,
    DocumentStatus,
    EvidenceMode,
    HealthLabel,
    KPIDomain,
    ProcessingJobStatus,
    TrendDirection,
)
from stratiq.infrastructure.db.models import (
    AuditEventModel,
    ChatMessageModel,
    ChatSessionModel,
    ChunkModel,
    DecisionCardModel,
    DocumentModel,
    ExecutiveReportModel,
    KPIModel,
    ProcessingJobModel,
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
        quality_warnings=list(m.quality_warnings or []),
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
    try:
        confidence = float(m.confidence)
    except (TypeError, ValueError):
        confidence = 0.5
    try:
        trend = TrendDirection(m.trend)
    except ValueError:
        trend = TrendDirection.unknown
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
        raw_extraction=m.raw_extraction or {},
        created_at=m.created_at,
        updated_at=m.updated_at,
        business_meaning=m.business_meaning,
        confidence=confidence,
        dimensions=m.dimensions or {},
        previous_value=m.previous_value,
        previous_period=m.previous_period,
        trend=trend,
        delta_label=m.delta_label,
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
            quality_warnings=doc.quality_warnings or [],
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
        quality_warnings: list[dict[str, Any]] | None = None,
    ) -> None:
        values: dict[str, Any] = {"status": status.value, "updated_at": datetime.now(UTC)}
        if error_message is not None:
            values["error_message"] = error_message
        if quality_warnings is not None:
            values["quality_warnings"] = quality_warnings
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

    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        await self._session.execute(delete(ChunkModel).where(ChunkModel.document_id == document_id))
        await self._session.flush()


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
                business_meaning=k.business_meaning,
                confidence=str(k.confidence),
                dimensions=k.dimensions or {},
                previous_value=k.previous_value,
                previous_period=k.previous_period,
                trend=k.trend.value,
                delta_label=k.delta_label,
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

    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        await self._session.execute(delete(KPIModel).where(KPIModel.document_id == document_id))
        await self._session.flush()


def _job_from_model(m: ProcessingJobModel) -> ProcessingJob:
    return ProcessingJob(
        id=m.id,
        document_id=m.document_id,
        owner_id=m.owner_id,
        status=ProcessingJobStatus(m.status),
        attempt=m.attempt,
        max_attempts=m.max_attempts,
        idempotency_key=m.idempotency_key,
        arq_job_id=m.arq_job_id,
        error_message=m.error_message,
        created_at=m.created_at,
        updated_at=m.updated_at,
        started_at=m.started_at,
        finished_at=m.finished_at,
        correlation_id=m.correlation_id,
    )


class ProcessingJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, job: ProcessingJob) -> ProcessingJob:
        model = ProcessingJobModel(
            id=job.id,
            document_id=job.document_id,
            owner_id=job.owner_id,
            status=job.status.value,
            attempt=job.attempt,
            max_attempts=job.max_attempts,
            idempotency_key=job.idempotency_key,
            arq_job_id=job.arq_job_id,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            correlation_id=job.correlation_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _job_from_model(model)

    async def get_by_id(self, job_id: uuid.UUID) -> ProcessingJob | None:
        result = await self._session.execute(
            select(ProcessingJobModel).where(ProcessingJobModel.id == job_id)
        )
        model = result.scalar_one_or_none()
        return _job_from_model(model) if model else None

    async def get_active_for_document(self, document_id: uuid.UUID) -> ProcessingJob | None:
        result = await self._session.execute(
            select(ProcessingJobModel)
            .where(
                ProcessingJobModel.document_id == document_id,
                ProcessingJobModel.status.in_(
                    [ProcessingJobStatus.queued.value, ProcessingJobStatus.running.value]
                ),
            )
            .order_by(ProcessingJobModel.created_at.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return _job_from_model(model) if model else None

    async def list_by_document(self, document_id: uuid.UUID, owner_id: uuid.UUID) -> list[ProcessingJob]:
        result = await self._session.execute(
            select(ProcessingJobModel)
            .where(
                ProcessingJobModel.document_id == document_id,
                ProcessingJobModel.owner_id == owner_id,
            )
            .order_by(ProcessingJobModel.created_at.desc())
        )
        return [_job_from_model(m) for m in result.scalars().all()]

    async def list_dead_letters(self, owner_id: uuid.UUID, limit: int = 50) -> list[ProcessingJob]:
        result = await self._session.execute(
            select(ProcessingJobModel)
            .where(
                ProcessingJobModel.owner_id == owner_id,
                ProcessingJobModel.status == ProcessingJobStatus.dead_letter.value,
            )
            .order_by(ProcessingJobModel.updated_at.desc())
            .limit(limit)
        )
        return [_job_from_model(m) for m in result.scalars().all()]

    async def update(
        self,
        job_id: uuid.UUID,
        *,
        status: ProcessingJobStatus | None = None,
        attempt: int | None = None,
        arq_job_id: str | None = None,
        error_message: str | None = None,
        clear_error: bool = False,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> None:
        values: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if status is not None:
            values["status"] = status.value
        if attempt is not None:
            values["attempt"] = attempt
        if arq_job_id is not None:
            values["arq_job_id"] = arq_job_id
        if clear_error:
            values["error_message"] = None
        elif error_message is not None:
            values["error_message"] = error_message
        if started_at is not None:
            values["started_at"] = started_at
        if finished_at is not None:
            values["finished_at"] = finished_at
        if correlation_id is not None:
            values["correlation_id"] = correlation_id
        await self._session.execute(
            update(ProcessingJobModel).where(ProcessingJobModel.id == job_id).values(**values)
        )
        await self._session.flush()


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


def _card_from_model(m: DecisionCardModel) -> DecisionCard:
    return DecisionCard(
        id=m.id,
        owner_id=m.owner_id,
        kpi_id=m.kpi_id,
        document_id=m.document_id,
        kpi_name=m.kpi_name,
        current_value=m.current_value,
        unit=m.unit,
        period=m.period,
        domain=m.domain,
        trend=TrendDirection(m.trend),
        health=HealthLabel(m.health),
        topic=m.topic or "",
        what_happened=m.what_happened,
        why_it_happened=m.why_it_happened,
        business_impact=m.business_impact or "",
        risks=list(m.risks or []),
        opportunities=list(m.opportunities or []),
        recommendation=m.recommendation,
        expected_outcome=m.expected_outcome or "",
        forecast_value=m.forecast_value,
        forecast_horizon=m.forecast_horizon,
        forecast_explanation=m.forecast_explanation,
        confidence=float(m.confidence or 0.5),
        evidence_mode=EvidenceMode(m.evidence_mode or EvidenceMode.evidence.value),
        evidence_chunk_ids=[uuid.UUID(str(x)) for x in (m.evidence_chunk_ids or [])],
        related_kpi_ids=[uuid.UUID(str(x)) for x in (m.related_kpi_ids or [])],
        created_at=m.created_at,
    )


def _report_from_model(m: ExecutiveReportModel) -> ExecutiveReport:
    return ExecutiveReport(
        id=m.id,
        owner_id=m.owner_id,
        summary=m.summary,
        health_score=m.health_score,
        health_label=HealthLabel(m.health_label),
        timeline=list(m.timeline or []),
        document_id=m.document_id,
        confidence=float(m.confidence or 0.5),
        created_at=m.created_at,
    )


class DecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_cards(
        self,
        owner_id: uuid.UUID,
        cards: list[DecisionCard],
        document_id: uuid.UUID | None = None,
    ) -> list[DecisionCard]:
        stmt = delete(DecisionCardModel).where(DecisionCardModel.owner_id == owner_id)
        if document_id is not None:
            stmt = stmt.where(DecisionCardModel.document_id == document_id)
        await self._session.execute(stmt)
        models = []
        for card in cards:
            model = DecisionCardModel(
                id=card.id,
                owner_id=owner_id,
                kpi_id=card.kpi_id,
                document_id=card.document_id,
                kpi_name=card.kpi_name,
                current_value=card.current_value,
                unit=card.unit,
                period=card.period,
                domain=card.domain,
                trend=card.trend.value,
                health=card.health.value,
                topic=card.topic,
                what_happened=card.what_happened,
                why_it_happened=card.why_it_happened,
                business_impact=card.business_impact,
                risks=card.risks,
                opportunities=card.opportunities,
                recommendation=card.recommendation,
                expected_outcome=card.expected_outcome,
                forecast_value=card.forecast_value,
                forecast_horizon=card.forecast_horizon,
                forecast_explanation=card.forecast_explanation,
                confidence=str(card.confidence),
                evidence_mode=card.evidence_mode.value,
                evidence_chunk_ids=[str(x) for x in card.evidence_chunk_ids],
                related_kpi_ids=[str(x) for x in card.related_kpi_ids],
                created_at=card.created_at or datetime.now(UTC),
            )
            self._session.add(model)
            models.append(model)
        await self._session.flush()
        return [_card_from_model(m) for m in models]

    async def list_cards(
        self, owner_id: uuid.UUID, document_id: uuid.UUID | None = None
    ) -> list[DecisionCard]:
        stmt = select(DecisionCardModel).where(DecisionCardModel.owner_id == owner_id)
        if document_id is not None:
            stmt = stmt.where(DecisionCardModel.document_id == document_id)
        stmt = stmt.order_by(DecisionCardModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [_card_from_model(m) for m in result.scalars().all()]

    async def get_card(self, card_id: uuid.UUID, owner_id: uuid.UUID) -> DecisionCard | None:
        result = await self._session.execute(
            select(DecisionCardModel).where(
                DecisionCardModel.id == card_id, DecisionCardModel.owner_id == owner_id
            )
        )
        model = result.scalar_one_or_none()
        return _card_from_model(model) if model else None

    async def save_executive_report(self, report: ExecutiveReport) -> ExecutiveReport:
        model = ExecutiveReportModel(
            id=report.id,
            owner_id=report.owner_id,
            document_id=report.document_id,
            summary=report.summary,
            health_score=report.health_score,
            health_label=report.health_label.value,
            timeline=report.timeline,
            confidence=str(report.confidence),
            created_at=report.created_at or datetime.now(UTC),
        )
        self._session.add(model)
        await self._session.flush()
        return _report_from_model(model)

    async def get_latest_executive_report(
        self, owner_id: uuid.UUID, document_id: uuid.UUID | None = None
    ) -> ExecutiveReport | None:
        stmt = select(ExecutiveReportModel).where(ExecutiveReportModel.owner_id == owner_id)
        if document_id is not None:
            stmt = stmt.where(ExecutiveReportModel.document_id == document_id)
        stmt = stmt.order_by(ExecutiveReportModel.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _report_from_model(model) if model else None
