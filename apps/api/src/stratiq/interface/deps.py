"""FastAPI dependency injection helpers."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from stratiq.application.audit import AuditService
from stratiq.application.auth import AuthService
from stratiq.application.chat import ChatService
from stratiq.application.dashboard import DashboardService
from stratiq.application.decisions import DecisionIntelligenceService
from stratiq.application.documents import DocumentService
from stratiq.application.kpis import KPIService
from stratiq.application.reports import ReportService
from stratiq.config import Settings, get_settings
from stratiq.domain.entities import User
from stratiq.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    EvidenceRequiredError,
    NotFoundError,
    ProcessingError,
    StorageError,
    ValidationError,
)
from stratiq.infrastructure.ai.embeddings import OpenAIEmbeddingClient
from stratiq.infrastructure.ai.llm import OpenAILLMClient
from stratiq.infrastructure.auth.security import SecurityHelper
from stratiq.infrastructure.chunking.semantic import SemanticChunker
from stratiq.infrastructure.db.repositories import (
    AuditRepository,
    ChatMessageRepository,
    ChatSessionRepository,
    ChunkRepository,
    DecisionRepository,
    DocumentRepository,
    KPIRepository,
    ProcessingJobRepository,
    UserRepository,
)
from stratiq.infrastructure.db.session import get_db_session
from stratiq.infrastructure.parsers.factory import ParserFactory
from stratiq.infrastructure.queue.tasks import ArqTaskQueue
from stratiq.infrastructure.redis_client import get_redis
from stratiq.infrastructure.storage.local import LocalFileStorage
from stratiq.infrastructure.vector.qdrant_store import QdrantVectorStore

_bearer = HTTPBearer(auto_error=False)


def _domain_exception_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AuthenticationError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    if isinstance(exc, AuthorizationError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, (ValidationError, EvidenceRequiredError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, (ProcessingError, StorageError)):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error.")


# ── Database session ──────────────────────────────────────────────────────────

DbSession = Annotated[object, Depends(get_db_session)]


# ── Settings ──────────────────────────────────────────────────────────────────

SettingsDep = Annotated[Settings, Depends(get_settings)]


# ── Repository factories ──────────────────────────────────────────────────────

def get_user_repo(session=Depends(get_db_session)) -> UserRepository:
    return UserRepository(session)


def get_doc_repo(session=Depends(get_db_session)) -> DocumentRepository:
    return DocumentRepository(session)


def get_chunk_repo(session=Depends(get_db_session)) -> ChunkRepository:
    return ChunkRepository(session)


def get_kpi_repo(session=Depends(get_db_session)) -> KPIRepository:
    return KPIRepository(session)


def get_job_repo(session=Depends(get_db_session)) -> ProcessingJobRepository:
    return ProcessingJobRepository(session)


def get_session_repo(session=Depends(get_db_session)) -> ChatSessionRepository:
    return ChatSessionRepository(session)


def get_message_repo(session=Depends(get_db_session)) -> ChatMessageRepository:
    return ChatMessageRepository(session)


def get_audit_repo(session=Depends(get_db_session)) -> AuditRepository:
    return AuditRepository(session)


def get_decision_repo(session=Depends(get_db_session)) -> DecisionRepository:
    return DecisionRepository(session)


# ── Infrastructure singletons ─────────────────────────────────────────────────

def get_security(settings: SettingsDep) -> SecurityHelper:
    return SecurityHelper(
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        access_ttl_minutes=settings.jwt_access_ttl_minutes,
        refresh_ttl_days=settings.jwt_refresh_ttl_days,
        redis_client=get_redis(),
    )


def get_storage(settings: SettingsDep) -> LocalFileStorage:
    return LocalFileStorage(settings.storage_path)


def get_task_queue(settings: SettingsDep) -> ArqTaskQueue:
    return ArqTaskQueue(settings.redis_url)


def get_llm(settings: SettingsDep) -> OpenAILLMClient:
    return OpenAILLMClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_chat_model,
    )


def get_embeddings(settings: SettingsDep) -> OpenAIEmbeddingClient:
    return OpenAIEmbeddingClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
    )


def get_vector_store(settings: SettingsDep) -> QdrantVectorStore:
    return QdrantVectorStore(settings.qdrant_url, settings.qdrant_collection)


# ── Service factories ─────────────────────────────────────────────────────────

def get_audit_service(audit_repo: AuditRepository = Depends(get_audit_repo)) -> AuditService:
    return AuditService(audit_repo)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    security: SecurityHelper = Depends(get_security),
    audit: AuditService = Depends(get_audit_service),
) -> AuthService:
    return AuthService(user_repo, security, audit)


def get_document_service(
    settings: SettingsDep,
    doc_repo: DocumentRepository = Depends(get_doc_repo),
    storage: LocalFileStorage = Depends(get_storage),
    queue: ArqTaskQueue = Depends(get_task_queue),
    audit: AuditService = Depends(get_audit_service),
    job_repo: ProcessingJobRepository = Depends(get_job_repo),
) -> DocumentService:
    return DocumentService(
        doc_repo,
        storage,
        queue,
        audit,
        job_repo=job_repo,
        max_attempts=settings.processing_max_tries,
    )


def get_kpi_service(
    kpi_repo: KPIRepository = Depends(get_kpi_repo),
) -> KPIService:
    return KPIService(kpi_repo)


def get_dashboard_service(
    kpi_repo: KPIRepository = Depends(get_kpi_repo),
    doc_repo: DocumentRepository = Depends(get_doc_repo),
) -> DashboardService:
    return DashboardService(kpi_repo, doc_repo)


def get_chat_service(
    settings: SettingsDep,
    session_repo: ChatSessionRepository = Depends(get_session_repo),
    message_repo: ChatMessageRepository = Depends(get_message_repo),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
    embeddings: OpenAIEmbeddingClient = Depends(get_embeddings),
    vectors: QdrantVectorStore = Depends(get_vector_store),
    llm: OpenAILLMClient = Depends(get_llm),
    audit: AuditService = Depends(get_audit_service),
) -> ChatService:
    return ChatService(
        session_repo=session_repo,
        message_repo=message_repo,
        chunk_repo=chunk_repo,
        embedding_client=embeddings,
        vector_store=vectors,
        llm_client=llm,
        qdrant_collection=settings.qdrant_collection,
        audit_service=audit,
    )


def get_decision_service(
    kpi_repo: KPIRepository = Depends(get_kpi_repo),
    doc_repo: DocumentRepository = Depends(get_doc_repo),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
    decision_repo: DecisionRepository = Depends(get_decision_repo),
    llm: OpenAILLMClient = Depends(get_llm),
    audit: AuditService = Depends(get_audit_service),
) -> DecisionIntelligenceService:
    return DecisionIntelligenceService(
        kpi_repo=kpi_repo,
        doc_repo=doc_repo,
        chunk_repo=chunk_repo,
        decision_repo=decision_repo,
        llm=llm,
        audit=audit,
    )


def get_report_service(
    decision_repo: DecisionRepository = Depends(get_decision_repo),
    audit: AuditService = Depends(get_audit_service),
) -> ReportService:
    return ReportService(decision_repo=decision_repo, audit=audit)


# ── Current user ──────────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    user_repo: UserRepository = Depends(get_user_repo),
    security: SecurityHelper = Depends(get_security),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header.")
    token = credentials.credentials
    try:
        payload = security.decode_access_token(token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    jti = payload.get("jti", "")
    if jti and await security.is_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked.")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    user = await user_repo.get_by_id(uuid.UUID(user_id_str))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is disabled.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
