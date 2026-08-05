from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from stratiq.domain.entities import (
    ChatMessage,
    ChatSession,
    Chunk,
    Citation,
    DecisionCard,
    Document,
    ExecutiveReport,
    KPI,
    User,
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
    UserModel,
)


def _user(m: UserModel) -> User:
    return User(
        id=m.id,
        email=m.email,
        password_hash=m.password_hash,
        full_name=m.full_name,
        created_at=m.created_at,
    )


def _document(m: DocumentModel) -> Document:
    return Document(
        id=m.id,
        owner_id=m.owner_id,
        filename=m.filename,
        content_type=m.content_type,
        storage_key=m.storage_key,
        status=m.status,
        document_type=m.document_type,
        domain=m.domain,
        domain_confidence=m.domain_confidence,
        error_message=m.error_message,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _chunk(m: ChunkModel) -> Chunk:
    return Chunk(
        id=m.id,
        document_id=m.document_id,
        ordinal=m.ordinal,
        content=m.content,
        token_estimate=m.token_estimate,
        metadata=m.metadata_json or {},
    )


def _kpi(m: KPIModel) -> KPI:
    return KPI(
        id=m.id,
        document_id=m.document_id,
        owner_id=m.owner_id,
        name=m.name,
        value=m.value,
        unit=m.unit,
        period=m.period,
        evidence_chunk_ids=list(m.evidence_chunk_ids or []),
        domain=m.domain,
        raw=m.raw or {},
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, email: str, password_hash: str, full_name: str) -> User:
        model = UserModel(email=email, password_hash=password_hash, full_name=full_name)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _user(model)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return _user(model) if model else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return _user(model) if model else None


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        model = DocumentModel(
            id=document.id,
            owner_id=document.owner_id,
            filename=document.filename,
            content_type=document.content_type,
            storage_key=document.storage_key,
            status=document.status,
            document_type=document.document_type,
            domain=document.domain,
            domain_confidence=document.domain_confidence,
            error_message=document.error_message,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _document(model)

    async def get(self, document_id: UUID, owner_id: UUID) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(
                DocumentModel.id == document_id, DocumentModel.owner_id == owner_id
            )
        )
        model = result.scalar_one_or_none()
        return _document(model) if model else None

    async def get_by_id(self, document_id: UUID) -> Document | None:
        model = await self._session.get(DocumentModel, document_id)
        return _document(model) if model else None

    async def list_for_owner(self, owner_id: UUID) -> list[Document]:
        result = await self._session.execute(
            select(DocumentModel)
            .where(DocumentModel.owner_id == owner_id)
            .order_by(DocumentModel.created_at.desc())
        )
        return [_document(m) for m in result.scalars().all()]

    async def update(self, document: Document) -> Document:
        model = await self._session.get(DocumentModel, document.id)
        if not model:
            raise ValueError("Document missing")
        model.status = document.status
        model.domain = document.domain
        model.domain_confidence = document.domain_confidence
        model.error_message = document.error_message
        await self._session.commit()
        await self._session.refresh(model)
        return _document(model)


class SqlAlchemyChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_document(self, document_id: UUID, chunks: list[Chunk]) -> list[Chunk]:
        await self._session.execute(delete(ChunkModel).where(ChunkModel.document_id == document_id))
        models = []
        for chunk in chunks:
            model = ChunkModel(
                id=chunk.id,
                document_id=document_id,
                ordinal=chunk.ordinal,
                content=chunk.content,
                token_estimate=chunk.token_estimate,
                metadata_json=chunk.metadata,
            )
            self._session.add(model)
            models.append(model)
        await self._session.commit()
        for model in models:
            await self._session.refresh(model)
        return [_chunk(m) for m in models]

    async def list_for_document(self, document_id: UUID) -> list[Chunk]:
        result = await self._session.execute(
            select(ChunkModel)
            .where(ChunkModel.document_id == document_id)
            .order_by(ChunkModel.ordinal)
        )
        return [_chunk(m) for m in result.scalars().all()]

    async def get_many(self, chunk_ids: list[UUID]) -> list[Chunk]:
        if not chunk_ids:
            return []
        result = await self._session.execute(select(ChunkModel).where(ChunkModel.id.in_(chunk_ids)))
        return [_chunk(m) for m in result.scalars().all()]


class SqlAlchemyKPIRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_document(self, document_id: UUID, kpis: list[KPI]) -> list[KPI]:
        await self._session.execute(delete(KPIModel).where(KPIModel.document_id == document_id))
        models = []
        for kpi in kpis:
            model = KPIModel(
                id=kpi.id,
                document_id=document_id,
                owner_id=kpi.owner_id,
                name=kpi.name,
                value=kpi.value,
                unit=kpi.unit,
                period=kpi.period,
                domain=kpi.domain,
                evidence_chunk_ids=kpi.evidence_chunk_ids,
                raw=kpi.raw,
            )
            self._session.add(model)
            models.append(model)
        await self._session.commit()
        for model in models:
            await self._session.refresh(model)
        return [_kpi(m) for m in models]

    async def list_for_owner(self, owner_id: UUID, document_id: UUID | None = None) -> list[KPI]:
        stmt = select(KPIModel).where(KPIModel.owner_id == owner_id)
        if document_id:
            stmt = stmt.where(KPIModel.document_id == document_id)
        stmt = stmt.order_by(KPIModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [_kpi(m) for m in result.scalars().all()]

    async def get(self, kpi_id: UUID, owner_id: UUID) -> KPI | None:
        result = await self._session.execute(
            select(KPIModel).where(KPIModel.id == kpi_id, KPIModel.owner_id == owner_id)
        )
        model = result.scalar_one_or_none()
        return _kpi(model) if model else None


class SqlAlchemyChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(self, owner_id: UUID, title: str) -> ChatSession:
        model = ChatSessionModel(owner_id=owner_id, title=title)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return ChatSession(
            id=model.id, owner_id=model.owner_id, title=model.title, created_at=model.created_at
        )

    async def get_session(self, session_id: UUID, owner_id: UUID) -> ChatSession | None:
        result = await self._session.execute(
            select(ChatSessionModel).where(
                ChatSessionModel.id == session_id, ChatSessionModel.owner_id == owner_id
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            return None
        return ChatSession(
            id=model.id, owner_id=model.owner_id, title=model.title, created_at=model.created_at
        )

    async def list_sessions(self, owner_id: UUID) -> list[ChatSession]:
        result = await self._session.execute(
            select(ChatSessionModel)
            .where(ChatSessionModel.owner_id == owner_id)
            .order_by(ChatSessionModel.created_at.desc())
        )
        return [
            ChatSession(id=m.id, owner_id=m.owner_id, title=m.title, created_at=m.created_at)
            for m in result.scalars().all()
        ]

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        citations: list[Citation] | None = None,
    ) -> ChatMessage:
        citation_payload = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "excerpt": c.excerpt,
                "score": c.score,
            }
            for c in (citations or [])
        ]
        model = ChatMessageModel(
            id=uuid4(),
            session_id=session_id,
            role=role,
            content=content,
            citations=citation_payload,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return ChatMessage(
            id=model.id,
            session_id=model.session_id,
            role=model.role,
            content=model.content,
            citations=citations or [],
            created_at=model.created_at,
        )

    async def list_messages(self, session_id: UUID, owner_id: UUID) -> list[ChatMessage]:
        session = await self.get_session(session_id, owner_id)
        if not session:
            return []
        result = await self._session.execute(
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc())
        )
        messages = []
        for m in result.scalars().all():
            citations = [
                Citation(
                    chunk_id=c.get("chunk_id", ""),
                    document_id=c.get("document_id", ""),
                    excerpt=c.get("excerpt", ""),
                    score=c.get("score"),
                )
                for c in (m.citations or [])
            ]
            messages.append(
                ChatMessage(
                    id=m.id,
                    session_id=m.session_id,
                    role=m.role,
                    content=m.content,
                    citations=citations,
                    created_at=m.created_at,
                )
            )
        return messages


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        action: str,
        actor_id: UUID | None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._session.add(
            AuditEventModel(
                action=action,
                actor_id=actor_id,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
            )
        )
        await self._session.commit()


def _card(m: DecisionCardModel) -> DecisionCard:
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
        trend=m.trend,
        health=m.health,
        what_happened=m.what_happened,
        why_it_happened=m.why_it_happened,
        risks=list(m.risks or []),
        opportunities=list(m.opportunities or []),
        recommendation=m.recommendation,
        forecast_value=m.forecast_value,
        forecast_horizon=m.forecast_horizon,
        forecast_explanation=m.forecast_explanation,
        evidence_chunk_ids=list(m.evidence_chunk_ids or []),
        related_kpi_ids=list(m.related_kpi_ids or []),
        created_at=m.created_at,
    )


def _report(m: ExecutiveReportModel) -> ExecutiveReport:
    return ExecutiveReport(
        id=m.id,
        owner_id=m.owner_id,
        summary=m.summary,
        health_score=m.health_score,
        health_label=m.health_label,
        timeline=list(m.timeline or []),
        document_id=m.document_id,
        created_at=m.created_at,
    )


class SqlAlchemyDecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_cards(
        self,
        owner_id: UUID,
        cards: list[DecisionCard],
        document_id: UUID | None = None,
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
                trend=card.trend,
                health=card.health,
                what_happened=card.what_happened,
                why_it_happened=card.why_it_happened,
                risks=card.risks,
                opportunities=card.opportunities,
                recommendation=card.recommendation,
                forecast_value=card.forecast_value,
                forecast_horizon=card.forecast_horizon,
                forecast_explanation=card.forecast_explanation,
                evidence_chunk_ids=card.evidence_chunk_ids,
                related_kpi_ids=card.related_kpi_ids,
            )
            self._session.add(model)
            models.append(model)
        await self._session.commit()
        for model in models:
            await self._session.refresh(model)
        return [_card(m) for m in models]

    async def list_cards(
        self, owner_id: UUID, document_id: UUID | None = None
    ) -> list[DecisionCard]:
        stmt = select(DecisionCardModel).where(DecisionCardModel.owner_id == owner_id)
        if document_id:
            stmt = stmt.where(DecisionCardModel.document_id == document_id)
        stmt = stmt.order_by(DecisionCardModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [_card(m) for m in result.scalars().all()]

    async def get_card(self, card_id: UUID, owner_id: UUID) -> DecisionCard | None:
        result = await self._session.execute(
            select(DecisionCardModel).where(
                DecisionCardModel.id == card_id, DecisionCardModel.owner_id == owner_id
            )
        )
        model = result.scalar_one_or_none()
        return _card(model) if model else None

    async def save_executive_report(self, report: ExecutiveReport) -> ExecutiveReport:
        model = ExecutiveReportModel(
            id=report.id,
            owner_id=report.owner_id,
            document_id=report.document_id,
            summary=report.summary,
            health_score=report.health_score,
            health_label=report.health_label,
            timeline=report.timeline,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _report(model)

    async def get_latest_executive_report(
        self, owner_id: UUID, document_id: UUID | None = None
    ) -> ExecutiveReport | None:
        stmt = select(ExecutiveReportModel).where(ExecutiveReportModel.owner_id == owner_id)
        if document_id:
            stmt = stmt.where(ExecutiveReportModel.document_id == document_id)
        stmt = stmt.order_by(ExecutiveReportModel.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _report(model) if model else None
