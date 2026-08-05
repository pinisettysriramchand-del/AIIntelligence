from pydantic import BaseModel


class KPIResponse(BaseModel):
    id: str
    document_id: str
    name: str
    value: str
    unit: str | None = None
    period: str | None = None
    domain: str | None = None
    evidence_chunk_ids: list[str]


class KPIListResponse(BaseModel):
    items: list[KPIResponse]
