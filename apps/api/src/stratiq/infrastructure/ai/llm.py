from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenAICompatibleLLM:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete_json(self, system: str, user: str) -> dict[str, Any]:
        text = await self.complete_text(system, user)
        return _parse_json_object(text)

    async def complete_text(self, system: str, user: str) -> str:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        payload = {
            "model": self._model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]


class OpenAICompatibleEmbeddings:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        vectors: list[list[float]] = []
        batch_size = 64
        async with httpx.AsyncClient(timeout=120.0) as client:
            for start in range(0, len(texts), batch_size):
                batch = texts[start : start + batch_size]
                response = await client.post(
                    f"{self._base_url}/embeddings",
                    headers=headers,
                    json={"model": self._model, "input": batch},
                )
                response.raise_for_status()
                data = response.json()
                ordered = sorted(data["data"], key=lambda item: item["index"])
                vectors.extend(item["embedding"] for item in ordered)
        return vectors


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("LLM did not return JSON object")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("LLM JSON was not an object")
    return value
