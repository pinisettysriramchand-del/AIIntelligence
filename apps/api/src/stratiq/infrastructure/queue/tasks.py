from __future__ import annotations

import logging
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings

from stratiq.config import get_settings

logger = logging.getLogger(__name__)


class ArqJobQueue:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            self._pool = await create_pool(RedisSettings.from_dsn(self._redis_url))
        return self._pool

    async def enqueue_process_document(self, document_id: str) -> str:
        pool = await self._get_pool()
        job = await pool.enqueue_job("process_document", document_id)
        job_id = job.job_id if job else "unknown"
        logger.info("enqueued process_document document_id=%s job_id=%s", document_id, job_id)
        return job_id


async def process_document(ctx: dict, document_id: str) -> None:
    from stratiq.application.processing import DocumentProcessingService
    from stratiq.infrastructure.ai.llm import OpenAICompatibleEmbeddings, OpenAICompatibleLLM
    from stratiq.infrastructure.db.repositories import (
        SqlAlchemyAuditRepository,
        SqlAlchemyChunkRepository,
        SqlAlchemyDecisionRepository,
        SqlAlchemyDocumentRepository,
        SqlAlchemyKPIRepository,
    )
    from stratiq.infrastructure.db.session import SessionLocal
    from stratiq.infrastructure.storage.local import LocalObjectStorage
    from stratiq.infrastructure.vector.qdrant_store import QdrantVectorStore

    settings = get_settings()
    async with SessionLocal() as session:
        service = DocumentProcessingService(
            documents=SqlAlchemyDocumentRepository(session),
            chunks=SqlAlchemyChunkRepository(session),
            kpis=SqlAlchemyKPIRepository(session),
            storage=LocalObjectStorage(settings.storage_path),
            embeddings=OpenAICompatibleEmbeddings(
                settings.openai_api_key,
                settings.openai_base_url,
                settings.openai_embedding_model,
            ),
            llm=OpenAICompatibleLLM(
                settings.openai_api_key,
                settings.openai_base_url,
                settings.openai_chat_model,
            ),
            vectors=QdrantVectorStore(settings.qdrant_url, settings.qdrant_collection),
            audit=SqlAlchemyAuditRepository(session),
            embedding_dimensions=settings.embedding_dimensions,
            decisions=SqlAlchemyDecisionRepository(session),
        )
        await service.process(UUID(document_id))
