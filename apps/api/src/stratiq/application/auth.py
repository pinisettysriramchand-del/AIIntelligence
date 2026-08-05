from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
import jwt

from stratiq.application.ports import AuditRepository, TokenStore, UserRepository
from stratiq.domain.entities import User
from stratiq.domain.enums import AuditAction
from stratiq.domain.exceptions import AuthenticationError, ConflictError, ValidationError

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        tokens: TokenStore,
        audit: AuditRepository,
        jwt_secret: str,
        jwt_algorithm: str,
        access_ttl_minutes: int,
        refresh_ttl_days: int,
    ) -> None:
        self._users = users
        self._tokens = tokens
        self._audit = audit
        self._secret = jwt_secret
        self._algorithm = jwt_algorithm
        self._access_ttl = access_ttl_minutes
        self._refresh_ttl = refresh_ttl_days

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    async def register(self, email: str, password: str, full_name: str) -> User:
        email = email.strip().lower()
        full_name = full_name.strip()
        if not EMAIL_RE.match(email):
            raise ValidationError("Invalid email address")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        if not full_name:
            raise ValidationError("Full name is required")
        existing = await self._users.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")
        user = await self._users.create(email, self.hash_password(password), full_name)
        await self._audit.record(AuditAction.USER_REGISTERED, user.id, "user", str(user.id))
        logger.info("user_registered user_id=%s", user.id)
        return user

    async def login(self, email: str, password: str) -> dict[str, str]:
        email = email.strip().lower()
        user = await self._users.get_by_email(email)
        if not user or not self.verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        tokens = await self._issue_tokens(user)
        await self._audit.record(AuditAction.USER_LOGIN, user.id, "user", str(user.id))
        return tokens

    async def refresh(self, refresh_token: str) -> dict[str, str]:
        payload = self._decode(refresh_token, expected_type="refresh")
        user_id = UUID(payload["sub"])
        token_id = payload["jti"]
        if not await self._tokens.is_refresh_valid(user_id, token_id):
            raise AuthenticationError("Refresh token revoked or expired")
        user = await self._users.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        await self._tokens.revoke_refresh(user_id, token_id)
        return await self._issue_tokens(user)

    async def logout(self, access_token: str, refresh_token: str | None = None) -> None:
        try:
            access = self._decode(access_token, expected_type="access")
        except AuthenticationError:
            return
        exp = access.get("exp")
        now = int(datetime.now(UTC).timestamp())
        ttl = max(int(exp) - now, 1) if exp else 60
        await self._tokens.blacklist_access(access["jti"], ttl)
        if refresh_token:
            try:
                refresh = self._decode(refresh_token, expected_type="refresh")
                await self._tokens.revoke_refresh(UUID(refresh["sub"]), refresh["jti"])
            except AuthenticationError:
                pass
        await self._audit.record(
            AuditAction.USER_LOGOUT,
            UUID(access["sub"]),
            "user",
            access["sub"],
        )

    async def resolve_user(self, access_token: str) -> User:
        payload = self._decode(access_token, expected_type="access")
        if await self._tokens.is_access_blacklisted(payload["jti"]):
            raise AuthenticationError("Token revoked")
        user = await self._users.get_by_id(UUID(payload["sub"]))
        if not user:
            raise AuthenticationError("User not found")
        return user

    async def _issue_tokens(self, user: User) -> dict[str, str]:
        now = datetime.now(UTC)
        access_jti = str(uuid4())
        refresh_jti = str(uuid4())
        access = jwt.encode(
            {
                "sub": str(user.id),
                "email": user.email,
                "type": "access",
                "jti": access_jti,
                "iat": now,
                "exp": now + timedelta(minutes=self._access_ttl),
            },
            self._secret,
            algorithm=self._algorithm,
        )
        refresh = jwt.encode(
            {
                "sub": str(user.id),
                "type": "refresh",
                "jti": refresh_jti,
                "iat": now,
                "exp": now + timedelta(days=self._refresh_ttl),
            },
            self._secret,
            algorithm=self._algorithm,
        )
        await self._tokens.store_refresh(
            user.id,
            refresh_jti,
            ttl_seconds=self._refresh_ttl * 24 * 3600,
        )
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
        }

    def _decode(self, token: str, expected_type: str) -> dict:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Invalid token") from exc
        if payload.get("type") != expected_type:
            raise AuthenticationError("Invalid token type")
        return payload
