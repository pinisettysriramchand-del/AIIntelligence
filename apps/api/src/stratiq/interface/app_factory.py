import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stratiq.config import get_settings
from stratiq.interface.routers import auth, chat, dashboard, decisions, documents, kpis, reports
from stratiq.interface.schemas.common import HealthResponse


def create_app(*, initialize_resources: bool = True) -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if initialize_resources:
            from stratiq.infrastructure.db.session import init_models

            Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
            await init_models()
        yield

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(kpis.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(decisions.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", app=settings.app_name)

    return app
