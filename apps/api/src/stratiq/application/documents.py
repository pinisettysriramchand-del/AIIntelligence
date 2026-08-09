"""Document use-cases: upload, list, get, delete, enqueue processing."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from stratiq.application.ports import ObjectStorage, TaskQueue
from stratiq.config import get_settings
from stratiq.domain.entities import Document, ProcessingJob
from stratiq.domain.enums import DocumentStatus, ProcessingJobStatus
from stratiq.domain.exceptions import AuthorizationError, NotFoundError

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        document_repo: "DocumentRepository",  # noqa: F821
        storage: ObjectStorage,
        task_queue: TaskQueue,
        audit_service: "AuditService",  # noqa: F821
        job_repo: "ProcessingJobRepository | None" = None,  # noqa: F821
        max_attempts: int | None = None,
    ) -> None:
        self._repo = document_repo
        self._storage = storage
        self._queue = task_queue
        self._audit = audit_service
        self._jobs = job_repo
        settings = get_settings()
        self._max_attempts = max_attempts if max_attempts is not None else settings.processing_max_tries

    async def upload(
        self,
        owner_id: uuid.UUID,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> Document:
        doc_id = uuid.uuid4()
        storage_key = f"{owner_id}/{doc_id}/{filename}"
        path = await self._storage.save(storage_key, data, content_type)

        now = datetime.now(UTC)
        doc = Document(
            id=doc_id,
            owner_id=owner_id,
            filename=filename,
            original_filename=filename,
            mime_type=content_type,
            size_bytes=len(data),
            storage_path=path,
            status=DocumentStatus.uploaded,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        await self._repo.save(doc)
        await self._audit.log_document_uploaded(owner_id, doc_id, filename)
        logger.info("Document uploaded", extra={"doc_id": str(doc_id), "owner_id": str(owner_id)})
        return doc

    async def enqueue_processing(self, doc_id: uuid.UUID, owner_id: uuid.UUID) -> ProcessingJob:
        """Queue (or return active) processing job — idempotent while queued/running."""
        doc = await self._get_owned(doc_id, owner_id)

        if self._jobs is not None:
            active = await self._jobs.get_active_for_document(doc_id)
            if active is not None:
                logger.info(
                    "Reusing active processing job",
                    extra={"doc_id": str(doc_id), "job_id": str(active.id)},
                )
                return active

        now = datetime.now(UTC)
        job_id = uuid.uuid4()
        idempotency_key = f"process:{doc_id}:{job_id}"
        job = ProcessingJob(
            id=job_id,
            document_id=doc_id,
            owner_id=owner_id,
            status=ProcessingJobStatus.queued,
            attempt=0,
            max_attempts=self._max_attempts,
            idempotency_key=idempotency_key,
            arq_job_id=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        if self._jobs is not None:
            await self._jobs.save(job)

        await self._repo.update_status(doc_id, DocumentStatus.processing, error_message="")
        arq_job_id = await self._queue.enqueue(
            "process_document",
            document_id=str(doc_id),
            processing_job_id=str(job_id),
            _job_id=idempotency_key,
        )
        if self._jobs is not None:
            await self._jobs.update(job_id, arq_job_id=arq_job_id)
            job.arq_job_id = arq_job_id

        logger.info(
            "Document queued for processing",
            extra={"doc_id": str(doc_id), "job_id": str(job_id), "arq_job_id": arq_job_id},
        )
        return job

    async def list_jobs(self, doc_id: uuid.UUID, owner_id: uuid.UUID) -> list[ProcessingJob]:
        await self._get_owned(doc_id, owner_id)
        if self._jobs is None:
            return []
        return await self._jobs.list_by_document(doc_id, owner_id)

    async def get_job(self, job_id: uuid.UUID, owner_id: uuid.UUID) -> ProcessingJob:
        if self._jobs is None:
            raise NotFoundError("ProcessingJob", job_id)
        job = await self._jobs.get_by_id(job_id)
        if job is None or job.owner_id != owner_id:
            raise NotFoundError("ProcessingJob", job_id)
        return job

    async def list_dead_letter_jobs(self, owner_id: uuid.UUID) -> list[ProcessingJob]:
        if self._jobs is None:
            return []
        return await self._jobs.list_dead_letters(owner_id)

    async def list_documents(self, owner_id: uuid.UUID) -> list[Document]:
        return await self._repo.list_by_owner(owner_id)

    async def get_document(self, doc_id: uuid.UUID, owner_id: uuid.UUID) -> Document:
        return await self._get_owned(doc_id, owner_id)

    async def delete_document(self, doc_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        doc = await self._get_owned(doc_id, owner_id)
        await self._storage.delete(doc.storage_path)
        await self._repo.delete(doc_id)

    async def _get_owned(self, doc_id: uuid.UUID, owner_id: uuid.UUID) -> Document:
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            raise NotFoundError("Document", doc_id)
        if doc.owner_id != owner_id:
            raise AuthorizationError("You do not own this document.")
        return doc
