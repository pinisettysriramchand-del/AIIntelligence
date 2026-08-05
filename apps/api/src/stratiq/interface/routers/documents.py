from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from stratiq.domain.entities import User
from stratiq.domain.exceptions import NotFoundError, ProcessingError, ValidationError
from stratiq.interface.deps import Services, get_current_user, get_services
from stratiq.interface.schemas.documents import DocumentListResponse, DocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_response(doc) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc.id),
        filename=doc.filename,
        content_type=doc.content_type,
        status=doc.status,
        document_type=doc.document_type,
        domain=doc.domain,
        domain_confidence=doc.domain_confidence,
        error_message=doc.error_message,
    )


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> DocumentResponse:
    data = await file.read()
    try:
        document = await services.documents.upload(
            owner_id=user.id,
            filename=file.filename or "upload.bin",
            data=data,
            content_type=file.content_type,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_response(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> DocumentListResponse:
    items = await services.documents.list(user.id)
    return DocumentListResponse(items=[_to_response(d) for d in items])


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> DocumentResponse:
    try:
        document = await services.documents.get(document_id, user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_response(document)


@router.post("/{document_id}/process", response_model=DocumentResponse)
async def process_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> DocumentResponse:
    try:
        document = await services.documents.enqueue_processing(document_id, user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProcessingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_response(document)
