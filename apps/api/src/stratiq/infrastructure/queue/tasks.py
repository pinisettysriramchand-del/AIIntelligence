"""ARQ task queue adapter and task definitions."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import Retry, func

from stratiq.application.ports import TaskQueue

logger = logging.getLogger(__name__)

DLQ_KEY_DEFAULT = "stratiq:dlq:process_document"


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
        job_id_override = kwargs.pop("_job_id", None)
        if job_id_override is not None:
            job = await pool.enqueue_job(function_name, **kwargs, _job_id=str(job_id_override))
        else:
            job = await pool.enqueue_job(function_name, **kwargs)
        job_id = job.job_id if job else str(job_id_override or uuid.uuid4())
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


async def _push_dlq(redis_url: str, dlq_key: str, payload: dict[str, Any]) -> None:
    client = aioredis.from_url(redis_url, decode_responses=True)
    try:
        await client.lpush(dlq_key, json.dumps(payload))
    finally:
        await client.aclose()


# ── Worker task functions ─────────────────────────────────────────────────────


async def process_document(
    ctx: dict[str, Any],
    document_id: str,
    processing_job_id: str | None = None,
) -> None:
    """ARQ worker task: run the document processing pipeline with retries + DLQ."""
    from stratiq.application.audit import AuditService
    from stratiq.application.processing import ProcessingService
    from stratiq.config import get_settings
    from stratiq.domain.enums import ProcessingJobStatus
    from stratiq.domain.exceptions import ProcessingError
    from stratiq.infrastructure.ai.embeddings import OpenAIEmbeddingClient
    from stratiq.infrastructure.ai.llm import OpenAILLMClient
    from stratiq.infrastructure.chunking.semantic import SemanticChunker
    from stratiq.infrastructure.db.repositories import (
        AuditRepository,
        ChunkRepository,
        DocumentRepository,
        KPIRepository,
        ProcessingJobRepository,
    )
    from stratiq.infrastructure.db.session import get_session_factory
    from stratiq.infrastructure.parsers.factory import ParserFactory
    from stratiq.infrastructure.storage.local import LocalFileStorage
    from stratiq.infrastructure.vector.qdrant_store import QdrantVectorStore

    settings = get_settings()
    max_attempts = settings.processing_max_tries
    defer_seconds = settings.processing_retry_defer_seconds
    job_try = int(ctx.get("job_try") or 1)
    job_uuid = uuid.UUID(processing_job_id) if processing_job_id else None
    session_factory = get_session_factory()
    now = datetime.now(UTC)

    async with session_factory() as db_session:
        jobs = ProcessingJobRepository(db_session)
        if job_uuid is not None:
            await jobs.update(
                job_uuid,
                status=ProcessingJobStatus.running,
                attempt=job_try,
                started_at=now if job_try == 1 else None,
                clear_error=True,
            )
            await db_session.commit()

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
            await service.process_document(
                uuid.UUID(document_id),
                attempt=job_try,
                max_attempts=max_attempts,
            )
            await db_session.commit()
        except Exception as exc:
            await db_session.rollback()
            error_text = str(exc)
            async with session_factory() as fail_session:
                fail_jobs = ProcessingJobRepository(fail_session)
                if job_try < max_attempts:
                    if job_uuid is not None:
                        await fail_jobs.update(
                            job_uuid,
                            status=ProcessingJobStatus.failed,
                            attempt=job_try,
                            error_message=error_text,
                        )
                        await fail_session.commit()
                    logger.warning(
                        "Processing attempt failed; retrying",
                        extra={
                            "doc_id": document_id,
                            "job_id": processing_job_id,
                            "attempt": job_try,
                            "max_attempts": max_attempts,
                        },
                    )
                    raise Retry(defer=job_try * defer_seconds) from exc

                if job_uuid is not None:
                    await fail_jobs.update(
                        job_uuid,
                        status=ProcessingJobStatus.dead_letter,
                        attempt=job_try,
                        error_message=error_text,
                        finished_at=datetime.now(UTC),
                    )
                    await fail_session.commit()
                await _push_dlq(
                    settings.redis_url,
                    settings.processing_dlq_key,
                    {
                        "document_id": document_id,
                        "processing_job_id": processing_job_id,
                        "attempt": job_try,
                        "max_attempts": max_attempts,
                        "error": error_text,
                        "failed_at": datetime.now(UTC).isoformat(),
                    },
                )
                logger.error(
                    "Processing moved to dead letter",
                    extra={
                        "doc_id": document_id,
                        "job_id": processing_job_id,
                        "attempt": job_try,
                    },
                )
            raise ProcessingError(error_text) from exc

    if job_uuid is not None:
        async with session_factory() as ok_session:
            await ProcessingJobRepository(ok_session).update(
                job_uuid,
                status=ProcessingJobStatus.succeeded,
                attempt=job_try,
                clear_error=True,
                finished_at=datetime.now(UTC),
            )
            await ok_session.commit()


process_document_job = func(process_document, name="process_document", max_tries=None)


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
