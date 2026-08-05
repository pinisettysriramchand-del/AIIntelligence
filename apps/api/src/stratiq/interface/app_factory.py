"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from stratiq.config import Settings
from stratiq.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    EvidenceRequiredError,
    NotFoundError,
    ProcessingError,
    StorageError,
    ValidationError,
)
from stratiq.infrastructure.db.session import close_db, init_db
from stratiq.infrastructure.redis_client import close_redis, init_redis
from stratiq.interface.routers import auth, chat, dashboard, documents, kpis

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    from stratiq.config import get_settings

    cfg = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("Starting %s", cfg.app_name)
        init_db(cfg.database_url)
        init_redis(cfg.redis_url)
        try:
            from stratiq.infrastructure.vector.qdrant_store import QdrantVectorStore

            qs = QdrantVectorStore(cfg.qdrant_url, cfg.qdrant_collection, cfg.openai_embedding_dimensions)
            await qs.ensure_collection()
        except Exception as exc:
            logger.warning("Qdrant not available at startup: %s", exc)
        yield
        logger.info("Shutting down %s", cfg.app_name)
        await close_db()
        await close_redis()

    app = FastAPI(
        title=cfg.app_name,
        version="1.0.0",
        description="StratIQ – AI-powered strategic intelligence platform API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _register_exception_handlers(app)

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(kpis.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": cfg.app_name}

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(AuthenticationError)
    async def auth_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(exc)})

    @app.exception_handler(AuthorizationError)
    async def authz_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(exc)})

    @app.exception_handler(EvidenceRequiredError)
    async def evidence_handler(request: Request, exc: EvidenceRequiredError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(exc)})

    @app.exception_handler(ProcessingError)
    async def processing_handler(request: Request, exc: ProcessingError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)})

    @app.exception_handler(StorageError)
    async def storage_handler(request: Request, exc: StorageError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(exc)})
