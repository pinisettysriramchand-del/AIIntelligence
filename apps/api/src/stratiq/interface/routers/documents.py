"""Documents router: upload, list, get, process, delete."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from stratiq.application.documents import DocumentService
from stratiq.config import Settings, get_settings
from stratiq.domain.exceptions import AuthorizationError, NotFoundError, StorageError
from stratiq.interface.deps import CurrentUser, get_document_service
from stratiq.interface.schemas.common import MessageResponse
from stratiq.interface.schemas.documents import DocumentListResponse, DocumentResponse

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


@router.post("/{doc_id}/process", response_model=MessageResponse)
async def process_document(
    doc_id: uuid.UUID,
    current_user: CurrentUser,
    doc_svc: DocumentService = Depends(get_document_service),
) -> MessageResponse:
    try:
        await doc_svc.enqueue_processing(doc_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return MessageResponse(message="Document queued for processing.")


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


def _doc_response(doc: object) -> DocumentResponse:
    from stratiq.domain.entities import Document

    assert isinstance(doc, Document)
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
    )
