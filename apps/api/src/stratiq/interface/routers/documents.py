"""Documents router: upload, list, get, process, delete."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from stratiq.application.documents import DocumentService
from stratiq.config import Settings, get_settings
from stratiq.domain.entities import Document, ProcessingJob
from stratiq.domain.exceptions import AuthorizationError, NotFoundError, StorageError
from stratiq.interface.deps import CurrentUser, get_document_service
from stratiq.interface.schemas.common import MessageResponse
from stratiq.interface.schemas.documents import (
    DocumentListResponse,
    DocumentResponse,
    ProcessingJobListResponse,
    ProcessingJobResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "application/csv",
}


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    current_user: CurrentUser,
    settings: Settings = Depends(get_settings),
    doc_svc: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    content_type = file.content_type or "application/octet-stream"
    if content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}. Allowed: PDF, XLSX, XLS, CSV.",
        )
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_bytes // (1024*1024)} MB.",
        )
    try:
        doc = await doc_svc.upload(
            owner_id=current_user.id,
            filename=file.filename or "unknown",
            content_type=content_type,
            data=data,
        )
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return _doc_response(doc)


@router.post("/{doc_id}/process", response_model=ProcessingJobResponse)
async def process_document(
    doc_id: uuid.UUID,
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> ProcessingJobResponse:
    try:
        job = await doc_svc.enqueue_processing(doc_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return _job_response(job)


@router.get("/jobs/dead-letter", response_model=ProcessingJobListResponse)
async def list_dead_letter_jobs(
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> ProcessingJobListResponse:
    jobs = await doc_svc.list_dead_letter_jobs(current_user.id)
    return ProcessingJobListResponse(items=[_job_response(j) for j in jobs], total=len(jobs))


@router.get("/jobs/{job_id}", response_model=ProcessingJobResponse)
async def get_processing_job(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> ProcessingJobResponse:
    try:
        job = await doc_svc.get_job(job_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _job_response(job)


@router.get("/{doc_id}/jobs", response_model=ProcessingJobListResponse)
async def list_document_jobs(
    doc_id: uuid.UUID,
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> ProcessingJobListResponse:
    try:
        jobs = await doc_svc.list_jobs(doc_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return ProcessingJobListResponse(items=[_job_response(j) for j in jobs], total=len(jobs))


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    docs = await doc_svc.list_documents(current_user.id)
    return DocumentListResponse(items=[_doc_response(d) for d in docs], total=len(docs))


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        doc = await doc_svc.get_document(doc_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return _doc_response(doc)


@router.delete("/{doc_id}", response_model=MessageResponse)
async def delete_document(
    doc_id: uuid.UUID,
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> MessageResponse:
    try:
        await doc_svc.delete_document(doc_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return MessageResponse(message="Document deleted.")


def _doc_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        owner_id=doc.owner_id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        status=doc.status,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        quality_warnings=doc.quality_warnings or [],
    )


def _job_response(job: ProcessingJob) -> ProcessingJobResponse:
    return ProcessingJobResponse(
        id=job.id,
        document_id=job.document_id,
        owner_id=job.owner_id,
        status=job.status.value,
        attempt=job.attempt,
        max_attempts=job.max_attempts,
        idempotency_key=job.idempotency_key,
        arq_job_id=job.arq_job_id,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )
