"""Auth use-cases: register, login, refresh, logout, me."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from stratiq.domain.entities import User
from stratiq.domain.exceptions import AuthenticationError, ConflictError

logger = logging.getLogger(__name__)


class AuthService:
    """Orchestrates authentication workflows."""

    def __init__(
        self,
        user_repo: "UserRepository",  # noqa: F821
        security: "SecurityHelper",  # noqa: F821
        audit_service: "AuditService",  # noqa: F821
    ) -> None:
        self._users = user_repo
        self._sec = security
        self._audit = audit_service

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        ip_address: str | None = None,
    ) -> User:
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise ConflictError(f"Email already registered: {email}")

        hashed = self._sec.hash_password(password)
        now = datetime.now(UTC)
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        await self._users.save(user)
        await self._audit.log_user_registered(user.id, email, ip_address)
        logger.info("User registered", extra={"user_id": str(user.id), "email": email})
        return user

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
    ) -> tuple[str, str]:
        """Return (access_token, refresh_token)."""
        user = await self._users.get_by_email(email)
        if user is None or not self._sec.verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("Account is disabled.")

        access_token = self._sec.create_access_token(str(user.id))
        refresh_token = await self._sec.create_refresh_token(str(user.id))
        await self._audit.log_user_login(user.id, ip_address)
        logger.info("User logged in", extra={"user_id": str(user.id)})
        return access_token, refresh_token

    async def refresh(self, refresh_token: str, ip_address: str | None = None) -> tuple[str, str]:
        """Rotate refresh token; return new (access_token, refresh_token)."""
        user_id = await self._sec.validate_and_consume_refresh_token(refresh_token)
        new_access = self._sec.create_access_token(user_id)
        new_refresh = await self._sec.create_refresh_token(user_id)
        await self._audit.log_token_refreshed(uuid.UUID(user_id), ip_address)
        return new_access, new_refresh

    async def logout(self, user_id: uuid.UUID, access_token: str, ip_address: str | None = None) -> None:
        await self._sec.blacklist_access_token(access_token)
        await self._audit.log_user_logout(user_id, ip_address)
        logger.info("User logged out", extra={"user_id": str(user_id)})

    async def get_current_user(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found.")
        return user
