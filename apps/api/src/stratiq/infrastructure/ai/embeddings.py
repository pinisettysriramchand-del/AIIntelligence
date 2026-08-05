"""OpenAI-compatible embeddings client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from stratiq.domain.exceptions import ProcessingError

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100


class OpenAIEmbeddingClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        dimensions: int = 1536,
        timeout: float = 60.0,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            vectors = await self._embed_batch(batch)
            all_vectors.extend(vectors)
        return all_vectors

    async def embed_one(self, text: str) -> list[float]:
        vectors = await self.embed([text])
        return vectors[0]

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload: dict[str, Any] = {"model": self._model, "input": texts}
        if self._dimensions:
            payload["dimensions"] = self._dimensions
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/embeddings",
                    headers=self._headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in sorted_data]
            except httpx.HTTPStatusError as exc:
                logger.error("Embeddings HTTP error: %s", exc.response.text)
                raise ProcessingError(f"Embedding request failed: {exc.response.status_code}") from exc
            except (KeyError, IndexError) as exc:
                raise ProcessingError(f"Embedding response parsing failed: {exc}") from exc
