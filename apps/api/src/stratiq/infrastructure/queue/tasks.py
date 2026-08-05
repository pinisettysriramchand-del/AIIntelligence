"""ARQ task queue adapter and task definitions."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings

from stratiq.application.ports import TaskQueue

logger = logging.getLogger(__name__)


class ArqTaskQueue:
    """TaskQueue port backed by ARQ."""

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._pool = None

    async def _get_pool(self) -> Any:
        if self._pool is None:
            settings = _parse_redis_settings(self._redis_url)
            self._pool = await create_pool(settings)
        return self._pool

    async def enqueue(self, function_name: str, **kwargs: Any) -> str:
        pool = await self._get_pool()
        job = await pool.enqueue_job(function_name, **kwargs)
        job_id = job.job_id if job else str(uuid.uuid4())
        logger.info("Job enqueued", extra={"function": function_name, "job_id": job_id})
        return job_id


def _parse_redis_settings(url: str) -> RedisSettings:
    import urllib.parse

    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    db = int(parsed.path.lstrip("/") or 0)
    password = parsed.password
    return RedisSettings(host=host, port=port, database=db, password=password)


# ── Worker task functions ─────────────────────────────────────────────────────


async def process_document(ctx: dict[str, Any], document_id: str) -> None:
    """ARQ worker task: run the document processing pipeline."""
    from stratiq.application.audit import AuditService
    from stratiq.application.processing import ProcessingService
    from stratiq.config import get_settings
    from stratiq.infrastructure.ai.embeddings import OpenAIEmbeddingClient
    from stratiq.infrastructure.ai.llm import OpenAILLMClient
    from stratiq.infrastructure.chunking.semantic import SemanticChunker
    from stratiq.infrastructure.db.repositories import (
        AuditRepository,
        ChunkRepository,
        DocumentRepository,
        KPIRepository,
    )
    from stratiq.infrastructure.db.session import get_session_factory
    from stratiq.infrastructure.parsers.factory import ParserFactory
    from stratiq.infrastructure.storage.local import LocalFileStorage
    from stratiq.infrastructure.vector.qdrant_store import QdrantVectorStore

    settings = get_settings()
    session_factory = get_session_factory()

    async with session_factory() as db_session:
        try:
            service = ProcessingService(
                document_repo=DocumentRepository(db_session),
                chunk_repo=ChunkRepository(db_session),
                kpi_repo=KPIRepository(db_session),
                storage=LocalFileStorage(settings.storage_path),
                parser_factory=ParserFactory(),
                chunker=SemanticChunker(settings.chunk_size, settings.chunk_overlap),
                embedding_client=OpenAIEmbeddingClient(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                    model=settings.openai_embedding_model,
                    dimensions=settings.openai_embedding_dimensions,
                ),
                vector_store=QdrantVectorStore(settings.qdrant_url, settings.qdrant_collection),
                llm_client=OpenAILLMClient(
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                    model=settings.openai_chat_model,
                ),
                qdrant_collection=settings.qdrant_collection,
                audit_service=AuditService(AuditRepository(db_session)),
            )
            await service.process_document(uuid.UUID(document_id))
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise


async def startup(ctx: dict[str, Any]) -> None:
    from stratiq.config import get_settings
    from stratiq.infrastructure.db.session import init_db

    settings = get_settings()
    init_db(settings.database_url)
    logger.info("ARQ worker started")


async def shutdown(ctx: dict[str, Any]) -> None:
    from stratiq.infrastructure.db.session import close_db

    await close_db()
    logger.info("ARQ worker shut down")
