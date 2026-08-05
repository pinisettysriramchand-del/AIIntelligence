"""JWT token creation/validation and password hashing."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from jose import JWTError, jwt
from passlib.context import CryptContext

from stratiq.domain.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

_REFRESH_PREFIX = "refresh:"
_BLACKLIST_PREFIX = "blacklist:"

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityHelper:
    def __init__(
        self,
        secret: str,
        algorithm: str,
        access_ttl_minutes: int,
        refresh_ttl_days: int,
        redis_client: "aioredis.Redis",
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._access_ttl = timedelta(minutes=access_ttl_minutes)
        self._refresh_ttl = timedelta(days=refresh_ttl_days)
        self._redis = redis_client

    # ── Password ──────────────────────────────────────────────────────────────

    def hash_password(self, plain: str) -> str:
        return _pwd_context.hash(plain)

    def verify_password(self, plain: str, hashed: str) -> bool:
        return _pwd_context.verify(plain, hashed)

    # ── Access token ──────────────────────────────────────────────────────────

    def create_access_token(self, user_id: str) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": user_id,
            "iat": now,
            "exp": now + self._access_ttl,
            "type": "access",
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            if payload.get("type") != "access":
                raise AuthenticationError("Not an access token.")
            return payload
        except JWTError as exc:
            raise AuthenticationError(f"Invalid token: {exc}") from exc

    async def blacklist_access_token(self, token: str) -> None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm], options={"verify_exp": False})
            jti = payload.get("jti", token[-16:])
            exp = payload.get("exp", 0)
            ttl_seconds = max(0, int(exp - datetime.now(UTC).timestamp())) + 60
            await self._redis.setex(f"{_BLACKLIST_PREFIX}{jti}", ttl_seconds, "1")
        except JWTError:
            pass

    async def is_blacklisted(self, jti: str) -> bool:
        return bool(await self._redis.exists(f"{_BLACKLIST_PREFIX}{jti}"))

    # ── Refresh token ─────────────────────────────────────────────────────────

    async def create_refresh_token(self, user_id: str) -> str:
        token = secrets.token_urlsafe(48)
        ttl_seconds = int(self._refresh_ttl.total_seconds())
        await self._redis.setex(f"{_REFRESH_PREFIX}{token}", ttl_seconds, user_id)
        return token

    async def validate_and_consume_refresh_token(self, token: str) -> str:
        key = f"{_REFRESH_PREFIX}{token}"
        user_id = await self._redis.get(key)
        if user_id is None:
            raise AuthenticationError("Refresh token is invalid or expired.")
        await self._redis.delete(key)
        if isinstance(user_id, bytes):
            user_id = user_id.decode()
        return user_id
