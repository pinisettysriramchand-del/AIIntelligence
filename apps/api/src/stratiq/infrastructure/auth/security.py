from __future__ import annotations

from uuid import UUID

from redis.asyncio import Redis


class RedisTokenStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _refresh_key(self, user_id: UUID, token_id: str) -> str:
        return f"refresh:{user_id}:{token_id}"

    def _blacklist_key(self, jti: str) -> str:
        return f"access_blacklist:{jti}"

    async def store_refresh(self, user_id: UUID, token_id: str, ttl_seconds: int) -> None:
        await self._redis.set(self._refresh_key(user_id, token_id), "1", ex=ttl_seconds)

    async def revoke_refresh(self, user_id: UUID, token_id: str) -> None:
        await self._redis.delete(self._refresh_key(user_id, token_id))

    async def is_refresh_valid(self, user_id: UUID, token_id: str) -> bool:
        return bool(await self._redis.exists(self._refresh_key(user_id, token_id)))

    async def blacklist_access(self, jti: str, ttl_seconds: int) -> None:
        await self._redis.set(self._blacklist_key(jti), "1", ex=ttl_seconds)

    async def is_access_blacklisted(self, jti: str) -> bool:
        return bool(await self._redis.exists(self._blacklist_key(jti)))
