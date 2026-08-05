from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    status: str
    document_type: str
    domain: str | None = None
    domain_confidence: float | None = None
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
