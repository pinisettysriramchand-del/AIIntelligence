"""OpenAI-compatible LLM client using httpx."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from stratiq.domain.exceptions import ProcessingError
from stratiq.infrastructure.observability import Timer, get_metrics

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class OpenAILLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        self._model = model
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        timer = Timer()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                usage = data.get("usage") or {}
                tokens = usage.get("total_tokens")
                get_metrics().record_ai_call(timer.ms(), tokens if isinstance(tokens, int) else None)
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as exc:
                get_metrics().record_ai_call(timer.ms())
                logger.error("LLM HTTP error: %s", exc.response.text)
                raise ProcessingError(f"LLM request failed: {exc.response.status_code}") from exc
            except (KeyError, IndexError, json.JSONDecodeError) as exc:
                get_metrics().record_ai_call(timer.ms())
                raise ProcessingError(f"LLM response parsing failed: {exc}") from exc

    async def json_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        text = await self.chat_completion(messages, temperature=temperature, max_tokens=max_tokens)
        return self._parse_json(text)

    def _parse_json(self, text: str) -> dict[str, Any]:
        match = _JSON_FENCE_RE.search(text)
        raw = match.group(1).strip() if match else text.strip()
        try:
            result = json.loads(raw)
            if not isinstance(result, dict):
                return {"_raw": result}
            return result
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned non-JSON: %s... error=%s", raw[:200], exc)
            return {}
