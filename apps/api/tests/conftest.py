from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from stratiq.application.auth import AuthService
from stratiq.application.chat import ChatService
from stratiq.application.decisions import DecisionIntelligenceService
from stratiq.application.documents import DocumentService
from stratiq.application.kpis import DashboardService, KPIService
from stratiq.application.reports import ReportService
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
from stratiq.domain.enums import DocumentStatus
from stratiq.interface.app_factory import create_app
from stratiq.interface.deps import Services, get_services


class InMemoryUsers:
    def __init__(self) -> None:
        self.items: dict[UUID, User] = {}

    async def create(self, email: str, password_hash: str, full_name: str) -> User:
        user = User(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            created_at=datetime.now(UTC),
        )
        self.items[user.id] = user
        return user

    async def get_by_email(self, email: str) -> User | None:
        for user in self.items.values():
            if user.email == email:
                return user
        return None

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.items.get(user_id)


class InMemoryDocuments:
    def __init__(self) -> None:
        self.items: dict[UUID, Document] = {}

    async def create(self, document: Document) -> Document:
        self.items[document.id] = document
        return document

    async def get(self, document_id: UUID, owner_id: UUID) -> Document | None:
        doc = self.items.get(document_id)
        if doc and doc.owner_id == owner_id:
            return doc
        return None

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return self.items.get(document_id)

    async def list_for_owner(self, owner_id: UUID) -> list[Document]:
        return [d for d in self.items.values() if d.owner_id == owner_id]

    async def update(self, document: Document) -> Document:
        self.items[document.id] = document
        return document


class InMemoryChunks:
    def __init__(self) -> None:
        self.items: dict[UUID, list[Chunk]] = {}

    async def replace_for_document(self, document_id: UUID, chunks: list[Chunk]) -> list[Chunk]:
        self.items[document_id] = chunks
        return chunks

    async def list_for_document(self, document_id: UUID) -> list[Chunk]:
        return self.items.get(document_id, [])

    async def get_many(self, chunk_ids: list[UUID]) -> list[Chunk]:
        found = []
        for chunks in self.items.values():
            for chunk in chunks:
                if chunk.id in chunk_ids:
                    found.append(chunk)
        return found


class InMemoryKPIs:
    def __init__(self) -> None:
        self.items: list[KPI] = []

    async def replace_for_document(self, document_id: UUID, kpis: list[KPI]) -> list[KPI]:
        self.items = [k for k in self.items if k.document_id != document_id] + kpis
        return kpis

    async def list_for_owner(self, owner_id: UUID, document_id: UUID | None = None) -> list[KPI]:
        result = [k for k in self.items if k.owner_id == owner_id]
        if document_id:
            result = [k for k in result if k.document_id == document_id]
        return result

    async def get(self, kpi_id: UUID, owner_id: UUID) -> KPI | None:
        for kpi in self.items:
            if kpi.id == kpi_id and kpi.owner_id == owner_id:
                return kpi
        return None


class InMemoryDecisions:
    def __init__(self) -> None:
        self.cards: list[DecisionCard] = []
        self.reports: list[ExecutiveReport] = []

    async def replace_cards(
        self,
        owner_id: UUID,
        cards: list[DecisionCard],
        document_id: UUID | None = None,
    ) -> list[DecisionCard]:
        kept = [c for c in self.cards if c.owner_id != owner_id]
        if document_id is not None:
            kept = [
                c
                for c in self.cards
                if not (c.owner_id == owner_id and c.document_id == document_id)
            ]
        self.cards = kept + cards
        return cards

    async def list_cards(
        self, owner_id: UUID, document_id: UUID | None = None
    ) -> list[DecisionCard]:
        result = [c for c in self.cards if c.owner_id == owner_id]
        if document_id:
            result = [c for c in result if c.document_id == document_id]
        return result

    async def get_card(self, card_id: UUID, owner_id: UUID) -> DecisionCard | None:
        for card in self.cards:
            if card.id == card_id and card.owner_id == owner_id:
                return card
        return None

    async def save_executive_report(self, report: ExecutiveReport) -> ExecutiveReport:
        self.reports.append(report)
        return report

    async def get_latest_executive_report(
        self, owner_id: UUID, document_id: UUID | None = None
    ) -> ExecutiveReport | None:
        items = [r for r in self.reports if r.owner_id == owner_id]
        if document_id:
            items = [r for r in items if r.document_id == document_id]
        return items[-1] if items else None


class InMemoryChats:
    def __init__(self) -> None:
        self.sessions: dict[UUID, ChatSession] = {}
        self.messages: dict[UUID, list[ChatMessage]] = {}

    async def create_session(self, owner_id: UUID, title: str) -> ChatSession:
        session = ChatSession(id=uuid4(), owner_id=owner_id, title=title, created_at=datetime.now(UTC))
        self.sessions[session.id] = session
        self.messages[session.id] = []
        return session

    async def get_session(self, session_id: UUID, owner_id: UUID) -> ChatSession | None:
        session = self.sessions.get(session_id)
        if session and session.owner_id == owner_id:
            return session
        return None

    async def list_sessions(self, owner_id: UUID) -> list[ChatSession]:
        return [s for s in self.sessions.values() if s.owner_id == owner_id]

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        citations: list[Citation] | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            id=uuid4(),
            session_id=session_id,
            role=role,
            content=content,
            citations=citations or [],
            created_at=datetime.now(UTC),
        )
        self.messages.setdefault(session_id, []).append(message)
        return message

    async def list_messages(self, session_id: UUID, owner_id: UUID) -> list[ChatMessage]:
        session = await self.get_session(session_id, owner_id)
        if not session:
            return []
        return self.messages.get(session_id, [])


class InMemoryAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def record(
        self,
        action: str,
        actor_id: UUID | None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "action": action,
                "actor_id": actor_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
            }
        )


class InMemoryTokens:
    def __init__(self) -> None:
        self.refresh: set[str] = set()
        self.blacklist: set[str] = set()

    async def store_refresh(self, user_id: UUID, token_id: str, ttl_seconds: int) -> None:
        self.refresh.add(f"{user_id}:{token_id}")

    async def revoke_refresh(self, user_id: UUID, token_id: str) -> None:
        self.refresh.discard(f"{user_id}:{token_id}")

    async def is_refresh_valid(self, user_id: UUID, token_id: str) -> bool:
        return f"{user_id}:{token_id}" in self.refresh

    async def blacklist_access(self, jti: str, ttl_seconds: int) -> None:
        self.blacklist.add(jti)

    async def is_access_blacklisted(self, jti: str) -> bool:
        return jti in self.blacklist


class InMemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        self.objects[key] = data
        return key

    async def get(self, key: str) -> bytes:
        return self.objects[key]

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)


class InMemoryJobs:
    def __init__(self) -> None:
        self.jobs: list[str] = []

    async def enqueue_process_document(self, document_id: str) -> str:
        self.jobs.append(document_id)
        return f"job-{document_id}"


class FakeEmbeddings:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 7), 0.1, 0.2] for t in texts]


class FakeLLM:
    async def complete_json(self, system: str, user: str) -> dict[str, Any]:
        if "Decision Intelligence" in system:
            # Extract first kpi id from user payload if present
            kpi_id = "00000000-0000-0000-0000-000000000001"
            for line in user.splitlines():
                if line.strip().startswith("- id="):
                    kpi_id = line.split("id=", 1)[1].split(" ", 1)[0]
                    break
            return {
                "executive_summary": "Performance is stable with actionable upside in revenue.",
                "health_score": 78,
                "timeline": [
                    {
                        "title": "Revenue review",
                        "detail": "Revenue held at target; monitor margin pressure.",
                        "severity": "medium",
                    }
                ],
                "cards": [
                    {
                        "kpi_id": kpi_id,
                        "kpi_name": "Revenue",
                        "trend": "up",
                        "health": "healthy",
                        "what_happened": "Revenue reached the reported value in the period.",
                        "why_it_happened": "Evidence indicates demand held and pricing remained stable.",
                        "risks": ["Margin compression if input costs rise"],
                        "opportunities": ["Expand top-performing channels"],
                        "recommendation": "Protect pricing discipline and scale winning channels.",
                        "forecast_value": "260",
                        "forecast_horizon": "next quarter",
                        "forecast_explanation": "Continuation of current demand trajectory.",
                        "evidence_chunk_ids": [],
                        "related_kpi_ids": [],
                    }
                ],
            }
        return {"industry": "Retail", "confidence": 0.9, "kpis": []}

    async def complete_text(self, system: str, user: str) -> str:
        return "Based on evidence, revenue is stable. [chunk:demo]"


class FakeVectors:
    def __init__(self) -> None:
        self.points: list[dict[str, Any]] = []

    async def ensure_collection(self, vector_size: int) -> None:
        return None

    async def upsert_chunks(self, points: list[dict[str, Any]]) -> None:
        self.points.extend(points)

    async def search(
        self,
        vector: list[float],
        owner_id: str,
        top_k: int,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        hits = []
        for point in self.points:
            payload = point["payload"]
            if payload.get("owner_id") != owner_id:
                continue
            if document_id and payload.get("document_id") != document_id:
                continue
            hits.append({"id": point["id"], "score": 0.9, "payload": payload})
            if len(hits) >= top_k:
                break
        return hits

    async def delete_document(self, document_id: str) -> None:
        self.points = [p for p in self.points if p["payload"].get("document_id") != document_id]


@pytest.fixture
def memory_stack():
    users = InMemoryUsers()
    documents = InMemoryDocuments()
    chunks = InMemoryChunks()
    kpis = InMemoryKPIs()
    chats = InMemoryChats()
    decisions = InMemoryDecisions()
    audit = InMemoryAudit()
    tokens = InMemoryTokens()
    storage = InMemoryStorage()
    jobs = InMemoryJobs()
    vectors = FakeVectors()
    embeddings = FakeEmbeddings()
    llm = FakeLLM()
    decision_service = DecisionIntelligenceService(
        kpis=kpis,
        documents=documents,
        chunks=chunks,
        decisions=decisions,
        llm=llm,
        audit=audit,
    )

    services = Services(
        auth=AuthService(
            users=users,
            tokens=tokens,
            audit=audit,
            jwt_secret="test-secret-key-please-change-32b!",
            jwt_algorithm="HS256",
            access_ttl_minutes=30,
            refresh_ttl_days=7,
        ),
        documents=DocumentService(documents=documents, storage=storage, jobs=jobs, audit=audit),
        kpis=KPIService(kpis=kpis),
        dashboard=DashboardService(kpis=kpis, documents=documents, decisions=decisions),
        chat=ChatService(
            chats=chats,
            chunks=chunks,
            embeddings=embeddings,
            llm=llm,
            vectors=vectors,
            audit=audit,
            top_k=5,
        ),
        decisions=decision_service,
        reports=ReportService(
            decisions=decisions,
            decision_service=decision_service,
            audit=audit,
        ),
    )
    return {
        "services": services,
        "documents": documents,
        "kpis": kpis,
        "chunks": chunks,
        "decisions": decisions,
        "jobs": jobs,
        "storage": storage,
        "vectors": vectors,
    }


@pytest.fixture
async def client(memory_stack):
    app = create_app(initialize_resources=False)

    async def override_services():
        yield memory_stack["services"]

    app.dependency_overrides[get_services] = override_services

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
