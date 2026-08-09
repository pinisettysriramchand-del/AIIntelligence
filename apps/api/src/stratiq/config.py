"""Application configuration via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "StratIQ"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://stratiq:stratiq@localhost:5432/stratiq"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "stratiq_chunks"

    # JWT
    jwt_secret: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 30
    jwt_refresh_ttl_days: int = 7

    # Storage
    storage_path: str = "/tmp/stratiq_storage"

    # OpenAI-compatible LLM
    openai_api_key: str = "sk-placeholder"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Processing
    chunk_size: int = 800
    chunk_overlap: int = 100
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB
    processing_max_tries: int = 3
    processing_retry_defer_seconds: int = 5
    processing_dlq_key: str = "stratiq:dlq:process_document"

    # OpenTelemetry (disabled by default; set OTEL_ENABLED=true)
    otel_enabled: bool = False
    otel_service_name: str = "stratiq-api"
    otel_exporter_otlp_endpoint: str = ""  # e.g. http://localhost:4318
    otel_traces_sampler_ratio: float = 1.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
