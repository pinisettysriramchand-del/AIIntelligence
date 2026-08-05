"""Chat use-cases: create session, list sessions, post message with RAG."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from stratiq.application.ports import EmbeddingClient, LLMClient, VectorStore
from stratiq.domain.entities import ChatMessage, ChatSession, Citation
from stratiq.domain.exceptions import AuthorizationError, NotFoundError

logger = logging.getLogger(__name__)

_RAG_SYSTEM_PROMPT = """You are StratIQ, an AI strategic intelligence assistant. 
Answer the user's question using ONLY the provided context chunks. 
Be concise, accurate, and cite your sources using [chunk_id] notation.
If you cannot answer from the context, say so clearly.

Context chunks:
{context}"""


class ChatService:
    def __init__(
        self,
        session_repo: "ChatSessionRepository",  # noqa: F821
        message_repo: "ChatMessageRepository",  # noqa: F821
        chunk_repo: "ChunkRepository",  # noqa: F821
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
        llm_client: LLMClient,
        qdrant_collection: str,
        audit_service: "AuditService",  # noqa: F821
    ) -> None:
        self._sessions = session_repo
        self._messages = message_repo
        self._chunks = chunk_repo
        self._embeddings = embedding_client
        self._vectors = vector_store
        self._llm = llm_client
        self._collection = qdrant_collection
        self._audit = audit_service

    async def create_session(self, owner_id: uuid.UUID, title: str) -> ChatSession:
        now = datetime.now(UTC)
        session = ChatSession(
            id=uuid.uuid4(),
            owner_id=owner_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        await self._sessions.save(session)
        await self._audit.log_chat_session_created(owner_id, session.id)
        logger.info("Chat session created", extra={"session_id": str(session.id)})
        return session

    async def list_sessions(self, owner_id: uuid.UUID) -> list[ChatSession]:
        return await self._sessions.list_by_owner(owner_id)

    async def get_session(self, session_id: uuid.UUID, owner_id: uuid.UUID) -> ChatSession:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise NotFoundError("ChatSession", session_id)
        if session.owner_id != owner_id:
            raise AuthorizationError("You do not own this session.")
        return session

    async def list_messages(self, session_id: uuid.UUID, owner_id: uuid.UUID) -> list[ChatMessage]:
        await self.get_session(session_id, owner_id)
        return await self._messages.list_by_session(session_id)

    async def post_message(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        user_content: str,
    ) -> ChatMessage:
        session = await self.get_session(session_id, owner_id)

        now = datetime.now(UTC)
        user_msg = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role="user",
            content=user_content,
            citations=[],
            created_at=now,
        )
        await self._messages.save(user_msg)

        query_vector = await self._embeddings.embed_one(user_content)
        search_results = await self._vectors.search(
            collection=self._collection,
            query_vector=query_vector,
            top_k=6,
            filter_payload={"owner_id": str(owner_id)},
        )

        citations: list[Citation] = []
        context_parts: list[str] = []
        seen_chunk_ids: set[str] = set()

        for result in search_results:
            payload = result.get("payload", {})
            chunk_id_str = result.get("id", "")
            if chunk_id_str in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id_str)

            content = payload.get("content", "")
            doc_id_str = payload.get("document_id", "")

            try:
                citation = Citation(
                    chunk_id=uuid.UUID(chunk_id_str),
                    document_id=uuid.UUID(doc_id_str),
                    excerpt=content[:300],
                )
                citations.append(citation)
                context_parts.append(f"[{chunk_id_str}]: {content}")
            except (ValueError, KeyError):
                continue

        history = await self._messages.list_by_session(session_id)
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": _RAG_SYSTEM_PROMPT.format(context="\n\n".join(context_parts)),
            }
        ]
        for hist_msg in history[-10:]:
            messages.append({"role": hist_msg.role, "content": hist_msg.content})

        assistant_text = await self._llm.chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )

        assistant_msg = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role="assistant",
            content=assistant_text,
            citations=citations,
            created_at=datetime.now(UTC),
        )
        await self._messages.save(assistant_msg)
        await self._audit.log_chat_message(owner_id, session_id, assistant_msg.id)
        logger.info(
            "Chat message answered",
            extra={"session_id": str(session_id), "citations": len(citations)},
        )
        return assistant_msg
