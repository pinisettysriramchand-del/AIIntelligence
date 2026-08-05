from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from stratiq.application.auth import AuthService
from stratiq.application.chat import ChatService
from stratiq.application.decisions import DecisionIntelligenceService
from stratiq.application.documents import DocumentService
from stratiq.application.kpis import DashboardService, KPIService
from stratiq.application.reports import ReportService
from stratiq.config import Settings, get_settings
from stratiq.domain.entities import User
from stratiq.domain.exceptions import AuthenticationError
from stratiq.infrastructure.ai.llm import OpenAICompatibleEmbeddings, OpenAICompatibleLLM
from stratiq.infrastructure.auth.security import RedisTokenStore
from stratiq.infrastructure.db.repositories import (
    SqlAlchemyAuditRepository,
    SqlAlchemyChatRepository,
    SqlAlchemyChunkRepository,
    SqlAlchemyDecisionRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyKPIRepository,
    SqlAlchemyUserRepository,
)
from stratiq.infrastructure.db.session import get_session
from stratiq.infrastructure.queue.tasks import ArqJobQueue
from stratiq.infrastructure.redis_client import create_redis
from stratiq.infrastructure.storage.local import LocalObjectStorage
from stratiq.infrastructure.vector.qdrant_store import QdrantVectorStore

_redis: Redis | None = None
_jobs: ArqJobQueue | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = create_redis()
    return _redis


async def get_job_queue(settings: Settings = Depends(get_settings)) -> ArqJobQueue:
    global _jobs
    if _jobs is None:
        _jobs = ArqJobQueue(settings.redis_url)
    return _jobs


@dataclass
class Services:
    auth: AuthService
    documents: DocumentService
    kpis: KPIService
    dashboard: DashboardService
    chat: ChatService
    decisions: DecisionIntelligenceService
    reports: ReportService


async def get_services(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    jobs: ArqJobQueue = Depends(get_job_queue),
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[Services, None]:
    users = SqlAlchemyUserRepository(session)
    documents = SqlAlchemyDocumentRepository(session)
    chunks = SqlAlchemyChunkRepository(session)
    kpis = SqlAlchemyKPIRepository(session)
    chats = SqlAlchemyChatRepository(session)
    decisions_repo = SqlAlchemyDecisionRepository(session)
    audit = SqlAlchemyAuditRepository(session)
    tokens = RedisTokenStore(redis)
    storage = LocalObjectStorage(settings.storage_path)
    embeddings = OpenAICompatibleEmbeddings(
        settings.openai_api_key, settings.openai_base_url, settings.openai_embedding_model
    )
    llm = OpenAICompatibleLLM(
        settings.openai_api_key, settings.openai_base_url, settings.openai_chat_model
    )
    vectors = QdrantVectorStore(settings.qdrant_url, settings.qdrant_collection)
    decision_service = DecisionIntelligenceService(
        kpis=kpis,
        documents=documents,
        chunks=chunks,
        decisions=decisions_repo,
        llm=llm,
        audit=audit,
    )

    yield Services(
        auth=AuthService(
            users=users,
            tokens=tokens,
            audit=audit,
            jwt_secret=settings.jwt_secret,
            jwt_algorithm=settings.jwt_algorithm,
            access_ttl_minutes=settings.jwt_access_ttl_minutes,
            refresh_ttl_days=settings.jwt_refresh_ttl_days,
        ),
        documents=DocumentService(
            documents=documents,
            storage=storage,
            jobs=jobs,
            audit=audit,
        ),
        kpis=KPIService(kpis=kpis),
        dashboard=DashboardService(
            kpis=kpis, documents=documents, decisions=decisions_repo
        ),
        chat=ChatService(
            chats=chats,
            chunks=chunks,
            embeddings=embeddings,
            llm=llm,
            vectors=vectors,
            audit=audit,
            top_k=settings.rag_top_k,
        ),
        decisions=decision_service,
        reports=ReportService(
            decisions=decisions_repo,
            decision_service=decision_service,
            audit=audit,
        ),
    )


async def get_current_user(
    authorization: str | None = Header(default=None),
    services: Services = Depends(get_services),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return await services.auth.resolve_user(token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
