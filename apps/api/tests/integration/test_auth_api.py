"""Integration tests for the auth API endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"new_{uuid.uuid4().hex[:8]}@example.com",
                "password": "securepassword",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["full_name"] == "New User"
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
        payload = {"email": email, "password": "password123", "full_name": "Dup User"}
        r1 = await client.post("/api/v1/auth/register", json=payload)
        assert r1.status_code == 201
        r2 = await client.post("/api/v1/auth/register", json=payload)
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "short", "full_name": "User"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "password123", "full_name": "User"},
        )
        assert response.status_code == 422


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, auth_client):
        client, headers = auth_client
        assert headers.get("Authorization", "").startswith("Bearer ")

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        email = f"login_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "correctpassword", "full_name": "Test"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_returns_tokens(self, client: AsyncClient):
        email = f"tok_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "password123", "full_name": "TokenUser"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


class TestMe:
    @pytest.mark.asyncio
    async def test_me_authenticated(self, auth_client):
        client, headers = auth_client
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "id" in data

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert response.status_code == 401


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "completely-invalid-token"},
        )
        assert response.status_code == 401


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_success(self, auth_client):
        client, headers = auth_client
        response = await client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient):
        response = await client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "api" in data
        assert "ai" in data
        assert "processing" in data
        assert "retrieval" in data
