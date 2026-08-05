"""Unit tests for SecurityHelper (JWT + password)."""

import pytest

from stratiq.domain.exceptions import AuthenticationError
from stratiq.infrastructure.auth.security import SecurityHelper
from tests.conftest import FakeRedis


@pytest.fixture
def security(fake_redis: FakeRedis) -> SecurityHelper:
    return SecurityHelper(
        secret="super-secret-test-key",
        algorithm="HS256",
        access_ttl_minutes=30,
        refresh_ttl_days=7,
        redis_client=fake_redis,
    )


class TestPasswordHashing:
    def test_hash_and_verify(self, security: SecurityHelper):
        hashed = security.hash_password("mysecretpassword")
        assert security.verify_password("mysecretpassword", hashed)

    def test_wrong_password_fails(self, security: SecurityHelper):
        hashed = security.hash_password("correcthorsebatterystaple")
        assert not security.verify_password("wrongpassword", hashed)

    def test_hashes_are_unique(self, security: SecurityHelper):
        h1 = security.hash_password("same")
        h2 = security.hash_password("same")
        assert h1 != h2


class TestAccessToken:
    def test_create_and_decode(self, security: SecurityHelper):
        token = security.create_access_token("user-123")
        payload = security.decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert "jti" in payload

    def test_invalid_token_raises(self, security: SecurityHelper):
        with pytest.raises(AuthenticationError):
            security.decode_access_token("not.a.valid.token")

    def test_tampered_token_raises(self, security: SecurityHelper):
        token = security.create_access_token("user-456")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(AuthenticationError):
            security.decode_access_token(tampered)


class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_create_and_consume(self, security: SecurityHelper):
        token = await security.create_refresh_token("user-789")
        assert len(token) > 20
        user_id = await security.validate_and_consume_refresh_token(token)
        assert user_id == "user-789"

    @pytest.mark.asyncio
    async def test_consume_twice_fails(self, security: SecurityHelper):
        token = await security.create_refresh_token("user-abc")
        await security.validate_and_consume_refresh_token(token)
        with pytest.raises(AuthenticationError):
            await security.validate_and_consume_refresh_token(token)

    @pytest.mark.asyncio
    async def test_invalid_refresh_token_fails(self, security: SecurityHelper):
        with pytest.raises(AuthenticationError):
            await security.validate_and_consume_refresh_token("totally-fake-token")


class TestBlacklist:
    @pytest.mark.asyncio
    async def test_blacklist_and_check(self, security: SecurityHelper):
        token = security.create_access_token("user-xyz")
        payload = security.decode_access_token(token)
        jti = payload["jti"]
        assert not await security.is_blacklisted(jti)
        await security.blacklist_access_token(token)
        assert await security.is_blacklisted(jti)
