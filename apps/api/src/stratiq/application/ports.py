"""Port interfaces (Protocols) for the application layer.

All concrete infrastructure adapters must satisfy these protocols.
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ObjectStorage(Protocol):
    """S3-compatible object storage port."""

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        """Persist *data* under *key*; return the resolved storage path."""
        ...

    async def load(self, key: str) -> bytes:
        """Return the raw bytes stored at *key*."""
        ...

    async def delete(self, key: str) -> None:
        """Remove the object at *key*."""
        ...

    async def exists(self, key: str) -> bool:
        """Return True if the object at *key* exists."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Vector database port."""

    async def upsert(
        self,
        collection: str,
        points: list[dict[str, Any]],
    ) -> None:
        """Insert or update vector points in *collection*."""
        ...

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int,
        filter_payload: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Return the *top_k* nearest neighbours from *collection*."""
        ...

    async def delete_by_document(self, collection: str, document_id: uuid.UUID) -> None:
        """Delete all points belonging to *document_id*."""
        ...


@runtime_checkable
class LLMClient(Protocol):
    """Language-model client port."""

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Return the assistant reply text."""
        ...

    async def json_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Return a JSON-parsed dict from the model output."""
        ...


@runtime_checkable
class EmbeddingClient(Protocol):
    """Text-embedding client port."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...

    async def embed_one(self, text: str) -> list[float]:
        """Return a single embedding vector."""
        ...


@runtime_checkable
class TaskQueue(Protocol):
    """Async task-queue port (ARQ-backed)."""

    async def enqueue(self, function_name: str, **kwargs: Any) -> str:
        """Enqueue a background task; return the job id."""
        ...
