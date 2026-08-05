from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from uuid import UUID, uuid4

from stratiq.application.ports import (
    AuditRepository,
    DocumentRepository,
    JobQueue,
    ObjectStorage,
)
from stratiq.domain.entities import Document
from stratiq.domain.enums import AuditAction, DocumentStatus, DocumentType
from stratiq.domain.exceptions import NotFoundError, ProcessingError, ValidationError

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".xls"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def detect_document_type(filename: str) -> DocumentType:
    ext = Path(filename).suffix.lower()
    mapping = {
        ".pdf": DocumentType.PDF,
        ".csv": DocumentType.CSV,
        ".xlsx": DocumentType.XLSX,
        ".xls": DocumentType.XLS,
    }
    return mapping.get(ext, DocumentType.UNKNOWN)


class DocumentService:
    def __init__(
        self,
        documents: DocumentRepository,
        storage: ObjectStorage,
        jobs: JobQueue,
        audit: AuditRepository,
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._jobs = jobs
        self._audit = audit

    async def upload(
        self,
        owner_id: UUID,
        filename: str,
        data: bytes,
        content_type: str | None,
    ) -> Document:
        filename = Path(filename).name
        if not filename:
            raise ValidationError("Filename is required")
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f"Unsupported file type: {ext}")
        if len(data) == 0:
            raise ValidationError("Empty file")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValidationError("File exceeds 25MB limit")

        doc_type = detect_document_type(filename)
        guessed = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        document_id = uuid4()
        storage_key = f"{owner_id}/{document_id}/{filename}"
        await self._storage.put(storage_key, data, guessed)

        document = Document(
            id=document_id,
            owner_id=owner_id,
            filename=filename,
            content_type=guessed,
            storage_key=storage_key,
            status=DocumentStatus.UPLOADED,
            document_type=doc_type,
        )
        saved = await self._documents.create(document)
        await self._audit.record(
            AuditAction.DOCUMENT_UPLOADED,
            owner_id,
            "document",
            str(saved.id),
            {"filename": filename, "bytes": len(data)},
        )
        logger.info("document_uploaded id=%s owner=%s", saved.id, owner_id)
        return saved

    async def list(self, owner_id: UUID) -> list[Document]:
        return await self._documents.list_for_owner(owner_id)

    async def get(self, document_id: UUID, owner_id: UUID) -> Document:
        document = await self._documents.get(document_id, owner_id)
        if not document:
            raise NotFoundError("Document not found")
        return document

    async def enqueue_processing(self, document_id: UUID, owner_id: UUID) -> Document:
        document = await self.get(document_id, owner_id)
        if document.status == DocumentStatus.PROCESSING:
            raise ProcessingError("Document is already processing")
        if document.status == DocumentStatus.READY:
            raise ProcessingError("Document already processed; re-upload to process again")

        document.status = DocumentStatus.PROCESSING
        document.error_message = None
        document = await self._documents.update(document)
        await self._jobs.enqueue_process_document(str(document.id))
        await self._audit.record(
            AuditAction.DOCUMENT_PROCESS_STARTED,
            owner_id,
            "document",
            str(document.id),
        )
        logger.info("document_process_enqueued id=%s", document.id)
        return document
