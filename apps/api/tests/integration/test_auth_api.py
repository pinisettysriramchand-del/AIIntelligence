import pytest


@pytest.mark.asyncio
async def test_register_login_me(client):
    register = await client.post(
        "/api/auth/register",
        json={"email": "ceo@example.com", "password": "password123", "full_name": "Ada CEO"},
    )
    assert register.status_code == 201
    assert register.json()["email"] == "ceo@example.com"

    login = await client.post(
        "/api/auth/login",
        json={"email": "ceo@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["full_name"] == "Ada CEO"
