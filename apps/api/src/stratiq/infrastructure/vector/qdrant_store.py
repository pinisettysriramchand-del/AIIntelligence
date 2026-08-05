from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    def __init__(self, url: str, collection: str) -> None:
        self._client = AsyncQdrantClient(url=url)
        self._collection = collection

    async def ensure_collection(self, vector_size: int) -> None:
        exists = await self._client.collection_exists(self._collection)
        if exists:
            return
        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
        )
        logger.info("qdrant_collection_created name=%s size=%s", self._collection, vector_size)

    async def upsert_chunks(self, points: list[dict[str, Any]]) -> None:
        if not points:
            return
        await self._client.upsert(
            collection_name=self._collection,
            points=[
                qmodels.PointStruct(
                    id=_point_id(point["id"]),
                    vector=point["vector"],
                    payload=point["payload"],
                )
                for point in points
            ],
        )

    async def search(
        self,
        vector: list[float],
        owner_id: str,
        top_k: int,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        must = [qmodels.FieldCondition(key="owner_id", match=qmodels.MatchValue(value=owner_id))]
        if document_id:
            must.append(
                qmodels.FieldCondition(
                    key="document_id", match=qmodels.MatchValue(value=document_id)
                )
            )
        results = await self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=top_k,
            query_filter=qmodels.Filter(must=must),
            with_payload=True,
        )
        return [
            {"id": str(hit.id), "score": hit.score, "payload": hit.payload or {}}
            for hit in results
        ]

    async def delete_document(self, document_id: str) -> None:
        exists = await self._client.collection_exists(self._collection)
        if not exists:
            return
        await self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id", match=qmodels.MatchValue(value=document_id)
                        )
                    ]
                )
            ),
        )


def _point_id(value: str) -> str:
    # Qdrant accepts UUID strings or unsigned ints; keep UUID string form.
    try:
        return str(UUID(value))
    except ValueError:
        return value
