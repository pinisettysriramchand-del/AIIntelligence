"""FastAPI application factory."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

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
from stratiq.infrastructure.observability import get_metrics
from stratiq.infrastructure.observability.correlation import (
    REQUEST_ID_HEADER,
    apply_to_current_span,
    install_log_filter,
    reset_correlation_id,
    resolve_incoming_request_id,
    set_correlation_id,
)
from stratiq.infrastructure.observability.otel import instrument_fastapi, setup_otel
from stratiq.infrastructure.redis_client import close_redis, init_redis
from stratiq.interface.routers import (
    ai_governance,
    auth,
    chat,
    dashboard,
    decisions,
    documents,
    kpis,
    reports,
)

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = resolve_incoming_request_id(request.headers)
        token = set_correlation_id(correlation_id)
        try:
            apply_to_current_span()
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = correlation_id
            return response
        finally:
            reset_correlation_id(token)


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response: Response | None = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            path = request.url.path
            # Collapse UUIDs to keep cardinality low
            parts = []
            for part in path.split("/"):
                if len(part) == 36 and part.count("-") == 4:
                    parts.append("{id}")
                else:
                    parts.append(part)
            normalized = "/".join(parts) or "/"
            duration_ms = (time.perf_counter() - start) * 1000.0
            get_metrics().record_request(request.method, normalized, status_code, duration_ms)


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
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RequestMetricsMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    _register_exception_handlers(app)

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(kpis.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(decisions.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(ai_governance.router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": cfg.app_name}

    @app.get("/metrics", tags=["observability"])
    async def metrics() -> dict:
        """Process-local MVP metrics (API latency, AI, processing, retrieval)."""
        snap = get_metrics().snapshot()
        from stratiq.infrastructure.observability.otel import is_otel_enabled

        snap["otel_enabled"] = is_otel_enabled()
        return snap

    install_log_filter()
    setup_otel(cfg)
    instrument_fastapi(app)

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
