from pydantic import BaseModel, Field


class CitationResponse(BaseModel):
    chunk_id: str
    document_id: str
    excerpt: str
    score: float | None = None


class ChatSessionResponse(BaseModel):
    id: str
    title: str


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: list[CitationResponse] = []


class CreateSessionRequest(BaseModel):
    title: str = Field(default="New analysis", max_length=200)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    document_id: str | None = None
