"""Qdrant vector store adapter implementing the VectorStore port."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from stratiq.domain.exceptions import ProcessingError

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    def __init__(self, url: str, collection: str, vector_size: int = 1536) -> None:
        self._client = AsyncQdrantClient(url=url)
        self._default_collection = collection
        self._vector_size = vector_size

    async def ensure_collection(self, collection: str | None = None) -> None:
        name = collection or self._default_collection
        try:
            existing = await self._client.get_collections()
            names = {c.name for c in existing.collections}
            if name not in names:
                await self._client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
                )
                logger.info("Qdrant collection created", extra={"collection": name})
        except Exception as exc:
            raise ProcessingError(f"Qdrant ensure_collection failed: {exc}") from exc

    async def upsert(self, collection: str, points: list[dict[str, Any]]) -> None:
        try:
            qdrant_points = [
                PointStruct(
                    id=p["id"],
                    vector=p["vector"],
                    payload=p.get("payload", {}),
                )
                for p in points
            ]
            await self._client.upsert(collection_name=collection, points=qdrant_points, wait=True)
            logger.debug("Qdrant upserted", extra={"collection": collection, "count": len(points)})
        except Exception as exc:
            raise ProcessingError(f"Qdrant upsert failed: {exc}") from exc

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int,
        filter_payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            qdrant_filter: Filter | None = None
            if filter_payload:
                conditions = [
                    FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filter_payload.items()
                ]
                qdrant_filter = Filter(must=conditions)

            results = await self._client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            return [
                {"id": str(hit.id), "score": hit.score, "payload": hit.payload or {}}
                for hit in results
            ]
        except Exception as exc:
            raise ProcessingError(f"Qdrant search failed: {exc}") from exc

    async def delete_by_document(self, collection: str, document_id: uuid.UUID) -> None:
        try:
            from qdrant_client.http.models import FilterSelector

            qdrant_filter = Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))]
            )
            await self._client.delete(
                collection_name=collection,
                points_selector=FilterSelector(filter=qdrant_filter),
            )
        except Exception as exc:
            raise ProcessingError(f"Qdrant delete_by_document failed: {exc}") from exc
