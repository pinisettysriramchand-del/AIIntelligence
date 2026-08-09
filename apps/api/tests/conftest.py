"""Shared pytest fixtures for unit and integration tests."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from stratiq.config import Settings
from stratiq.infrastructure.db.models import Base

# ── In-memory SQLite with a single shared connection (StaticPool) ─────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(
        database_url=TEST_DB_URL,
        redis_url="redis://localhost:6379/15",
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_chunks",
        jwt_secret="test-secret-key-for-tests-only-must-be-long-enough",
        jwt_access_ttl_minutes=60,
        jwt_refresh_ttl_days=7,
        storage_path="/tmp/stratiq_test_storage",
        openai_api_key="sk-test",
        openai_base_url="http://localhost:9999/v1",
        openai_chat_model="gpt-test",
        openai_embedding_model="embed-test",
        openai_embedding_dimensions=4,
        cors_origins=["http://localhost:3000"],
    )


@pytest_asyncio.fixture(scope="session")
async def db_engine(test_settings: Settings):
    """Session-scoped engine with StaticPool so all tests share the same SQLite :memory: db."""
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


# ── Fake infrastructure ───────────────────────────────────────────────────────

class FakeStorage:
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        self._store[key] = data
        return key

    async def load(self, key: str) -> bytes:
        if key not in self._store:
            from stratiq.domain.exceptions import StorageError
            raise StorageError(f"Not found: {key}")
        return self._store[key]

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._store


class FakeLLMClient:
    def __init__(self, chat_response: str = "Test answer", json_response: dict[str, Any] | None = None) -> None:
        self._chat = chat_response
        self._json = json_response or {}

    async def chat_completion(self, messages: list, temperature: float = 0.7, max_tokens: int = 1024) -> str:
        return self._chat

    async def json_completion(self, messages: list, temperature: float = 0.0, max_tokens: int = 1024) -> dict:
        return self._json


class FakeEmbeddingClient:
    def __init__(self, dims: int = 4) -> None:
        self._dims = dims

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self._dims for _ in texts]

    async def embed_one(self, text: str) -> list[float]:
        return [0.1] * self._dims


class FakeVectorStore:
    def __init__(self) -> None:
        self._points: list[dict] = []

    async def upsert(self, collection: str, points: list[dict]) -> None:
        self._points.extend(points)

    async def search(
        self, collection: str, query_vector: list, top_k: int, filter_payload: dict | None = None
    ) -> list[dict]:
        return []

    async def delete_by_document(self, collection: str, document_id: uuid.UUID) -> None:
        self._points = [
            p for p in self._points if p.get("payload", {}).get("document_id") != str(document_id)
        ]


class FakeTaskQueue:
    def __init__(self) -> None:
        self.jobs: list[dict] = []

    async def enqueue(self, function_name: str, **kwargs: Any) -> str:
        job_id = str(kwargs.pop("_job_id", None) or uuid.uuid4())
        self.jobs.append({"function": function_name, "kwargs": kwargs, "job_id": job_id})
        return job_id


class FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def setex(self, name: str, time: int, value: Any) -> None:
        self._store[name] = str(value).encode() if isinstance(value, str) else value

    async def get(self, name: str) -> bytes | None:
        return self._store.get(name)

    async def exists(self, name: str) -> int:
        return 1 if name in self._store else 0

    async def delete(self, name: str) -> None:
        self._store.pop(name, None)

    async def aclose(self) -> None:
        pass


class FakeAuditRepo:
    def __init__(self) -> None:
        self.events: list = []

    async def save(self, event: Any) -> None:
        self.events.append(event)


@pytest.fixture
def fake_storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def fake_embeddings() -> FakeEmbeddingClient:
    return FakeEmbeddingClient()


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def fake_queue() -> FakeTaskQueue:
    return FakeTaskQueue()


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
def fake_audit_repo() -> FakeAuditRepo:
    return FakeAuditRepo()


# ── App + HTTP client ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def app(test_settings: Settings, db_engine, fake_redis: FakeRedis) -> FastAPI:
    """FastAPI app wired to the shared SQLite engine + fake infrastructure."""
    from contextlib import asynccontextmanager
    from typing import AsyncGenerator as AG

    from stratiq.infrastructure.auth.security import SecurityHelper
    from stratiq.infrastructure.db.session import get_db_session
    from stratiq.interface import deps as _deps

    _session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _get_test_session() -> AsyncGenerator[AsyncSession, None]:
        async with _session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    _security = SecurityHelper(
        secret=test_settings.jwt_secret,
        algorithm=test_settings.jwt_algorithm,
        access_ttl_minutes=test_settings.jwt_access_ttl_minutes,
        refresh_ttl_days=test_settings.jwt_refresh_ttl_days,
        redis_client=fake_redis,
    )

    _fake_storage = FakeStorage()
    _fake_queue = FakeTaskQueue()

    @asynccontextmanager
    async def _noop_lifespan(application: FastAPI) -> AG[None, None]:
        yield

    from fastapi import FastAPI as _FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from stratiq.interface.app_factory import _register_exception_handlers
    from stratiq.interface.routers import auth, chat, dashboard, decisions, documents, kpis, reports

    _app = _FastAPI(title="StratIQ Test", lifespan=_noop_lifespan)
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _register_exception_handlers(_app)
    _app.include_router(auth.router, prefix="/api/v1")
    _app.include_router(documents.router, prefix="/api/v1")
    _app.include_router(kpis.router, prefix="/api/v1")
    _app.include_router(dashboard.router, prefix="/api/v1")
    _app.include_router(chat.router, prefix="/api/v1")
    _app.include_router(decisions.router, prefix="/api/v1")
    _app.include_router(reports.router, prefix="/api/v1")

    @_app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "service": "StratIQ Test"}

    @_app.get("/metrics")
    async def metrics() -> dict:
        from stratiq.infrastructure.observability import get_metrics

        return get_metrics().snapshot()

    # Wire overrides
    _app.dependency_overrides[get_db_session] = _get_test_session
    _app.dependency_overrides[_deps.get_settings] = lambda: test_settings
    _app.dependency_overrides[_deps.get_security] = lambda: _security
    _app.dependency_overrides[_deps.get_storage] = lambda: _fake_storage
    _app.dependency_overrides[_deps.get_task_queue] = lambda: _fake_queue

    return _app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncGenerator[tuple[AsyncClient, dict], None]:
    """Return (client, headers) for a freshly registered + logged-in user."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test User"},
    )
    assert reg.status_code == 201, f"Register failed: {reg.text}"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    yield client, headers


@pytest_asyncio.fixture
async def auth_headers(auth_client) -> dict[str, str]:
    _, headers = auth_client
    return headers


@pytest_asyncio.fixture
async def current_user_id(client: AsyncClient, auth_headers: dict[str, str]) -> uuid.UUID:
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    return uuid.UUID(me.json()["id"])
