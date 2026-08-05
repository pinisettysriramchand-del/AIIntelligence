"""Document use-cases: upload, list, get, delete, enqueue processing."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from stratiq.application.ports import ObjectStorage, TaskQueue
from stratiq.domain.entities import Document
from stratiq.domain.enums import DocumentStatus
from stratiq.domain.exceptions import AuthorizationError, NotFoundError

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        document_repo: "DocumentRepository",  # noqa: F821
        storage: ObjectStorage,
        task_queue: TaskQueue,
        audit_service: "AuditService",  # noqa: F821
    ) -> None:
        self._repo = document_repo
        self._storage = storage
        self._queue = task_queue
        self._audit = audit_service

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

    async def enqueue_processing(self, doc_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        doc = await self._get_owned(doc_id, owner_id)
        await self._repo.update_status(doc_id, DocumentStatus.processing)
        await self._queue.enqueue("process_document", document_id=str(doc_id))
        logger.info("Document queued for processing", extra={"doc_id": str(doc_id)})

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
