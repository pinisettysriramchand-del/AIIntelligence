from __future__ import annotations

import logging
from uuid import UUID

from stratiq.application.ports import (
    AuditRepository,
    ChatRepository,
    ChunkRepository,
    EmbeddingsPort,
    LLMPort,
    VectorStore,
)
from stratiq.domain.entities import ChatMessage, ChatSession, Citation
from stratiq.domain.enums import AuditAction
from stratiq.domain.exceptions import NotFoundError, ValidationError
from stratiq.infrastructure.ai import prompts

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        chats: ChatRepository,
        chunks: ChunkRepository,
        embeddings: EmbeddingsPort,
        llm: LLMPort,
        vectors: VectorStore,
        audit: AuditRepository,
        top_k: int,
    ) -> None:
        self._chats = chats
        self._chunks = chunks
        self._embeddings = embeddings
        self._llm = llm
        self._vectors = vectors
        self._audit = audit
        self._top_k = top_k

    async def create_session(self, owner_id: UUID, title: str) -> ChatSession:
        title = (title or "New analysis").strip()[:200] or "New analysis"
        return await self._chats.create_session(owner_id, title)

    async def list_sessions(self, owner_id: UUID) -> list[ChatSession]:
        return await self._chats.list_sessions(owner_id)

    async def list_messages(self, session_id: UUID, owner_id: UUID) -> list[ChatMessage]:
        session = await self._chats.get_session(session_id, owner_id)
        if not session:
            raise NotFoundError("Chat session not found")
        return await self._chats.list_messages(session_id, owner_id)

    async def ask(
        self,
        owner_id: UUID,
        question: str,
        session_id: UUID | None = None,
        document_id: UUID | None = None,
    ) -> ChatMessage:
        question = question.strip()
        if not question:
            raise ValidationError("Question is required")

        if session_id is None:
            session = await self.create_session(owner_id, question[:80])
            session_id = session.id
        else:
            session = await self._chats.get_session(session_id, owner_id)
            if not session:
                raise NotFoundError("Chat session not found")

        await self._chats.add_message(session_id, "user", question, [])

        query_vec = (await self._embeddings.embed([question]))[0]
        hits = await self._vectors.search(
            vector=query_vec,
            owner_id=str(owner_id),
            top_k=self._top_k,
            document_id=str(document_id) if document_id else None,
        )

        citations: list[Citation] = []
        evidence_blocks: list[str] = []
        for hit in hits:
            payload = hit.get("payload") or {}
            chunk_id = str(payload.get("chunk_id") or hit.get("id"))
            doc_id = str(payload.get("document_id") or "")
            content = str(payload.get("content") or "")
            excerpt = content[:400]
            citations.append(
                Citation(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    excerpt=excerpt,
                    score=hit.get("score"),
                )
            )
            evidence_blocks.append(f"[chunk:{chunk_id} doc:{doc_id}]\n{content}")

        if not evidence_blocks:
            answer = (
                "I could not find relevant evidence in your uploaded documents. "
                "Upload and process documents first, then ask again."
            )
            citations = []
        else:
            answer = await self._llm.complete_text(
                prompts.CHAT_SYSTEM,
                prompts.chat_user(question, "\n\n".join(evidence_blocks)),
            )

        message = await self._chats.add_message(session_id, "assistant", answer, citations)
        await self._audit.record(
            AuditAction.CHAT_MESSAGE,
            owner_id,
            "chat_session",
            str(session_id),
            {"question_len": len(question), "citation_count": len(citations)},
        )
        logger.info("chat_answered session=%s citations=%s", session_id, len(citations))
        return message
