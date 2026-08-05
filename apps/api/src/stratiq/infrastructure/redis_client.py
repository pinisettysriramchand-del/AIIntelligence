"""Redis async client factory."""

from __future__ import annotations

import redis.asyncio as aioredis

_redis_client: aioredis.Redis | None = None


def init_redis(redis_url: str) -> aioredis.Redis:
    global _redis_client
    _redis_client = aioredis.from_url(redis_url, decode_responses=False)
    return _redis_client


def get_redis() -> aioredis.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
