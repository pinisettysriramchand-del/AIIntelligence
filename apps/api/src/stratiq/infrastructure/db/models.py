"""SQLAlchemy ORM models (async, declarative).

Uses generic SQLAlchemy types (Uuid, JSON) that work with both PostgreSQL and SQLite,
enabling the test suite to run against an in-memory SQLite database.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import JSON as GenericJSON
from sqlalchemy import Uuid as GenericUuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GenericUuid(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    documents: Mapped[list[DocumentModel]] = relationship("DocumentModel", back_populates="owner", lazy="noload")
    chat_sessions: Mapped[list[ChatSessionModel]] = relationship(
        "ChatSessionModel", back_populates="owner", lazy="noload"
    )


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(GenericUuid(as_uuid=True), primary_key=True, default=_uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner: Mapped[UserModel] = relationship("UserModel", back_populates="documents", lazy="noload")
    chunks: Mapped[list[ChunkModel]] = relationship("ChunkModel", back_populates="document", lazy="noload")
    kpis: Mapped[list[KPIModel]] = relationship("KPIModel", back_populates="document", lazy="noload")


class ChunkModel(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(GenericUuid(as_uuid=True), primary_key=True, default=_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", GenericJSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document: Mapped[DocumentModel] = relationship("DocumentModel", back_populates="chunks", lazy="noload")


class KPIModel(Base):
    __tablename__ = "kpis"

    id: Mapped[uuid.UUID] = mapped_column(GenericUuid(as_uuid=True), primary_key=True, default=_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    value: Mapped[str] = mapped_column(String(512), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    period: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence_chunk_ids: Mapped[list[Any]] = mapped_column(GenericJSON, nullable=False, default=list)
    raw_extraction: Mapped[dict[str, Any]] = mapped_column(GenericJSON, nullable=False, default=dict)
    business_meaning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False, default="0.5")
    dimensions: Mapped[dict[str, Any]] = mapped_column(GenericJSON, nullable=False, default=dict)
    previous_value: Mapped[str | None] = mapped_column(String(512), nullable=True)
    previous_period: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trend: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    delta_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    document: Mapped[DocumentModel] = relationship("DocumentModel", back_populates="kpis", lazy="noload")


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(GenericUuid(as_uuid=True), primary_key=True, default=_uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner: Mapped[UserModel] = relationship("UserModel", back_populates="chat_sessions", lazy="noload")
    messages: Mapped[list[ChatMessageModel]] = relationship(
        "ChatMessageModel", back_populates="session", lazy="noload"
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(GenericUuid(as_uuid=True), primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[Any]] = mapped_column(GenericJSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session: Mapped[ChatSessionModel] = relationship("ChatSessionModel", back_populates="messages", lazy="noload")


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(GenericUuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(GenericJSON, nullable=False, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DecisionCardModel(Base):
    __tablename__ = "decision_cards"

    id: Mapped[uuid.UUID] = mapped_column(GenericUuid(as_uuid=True), primary_key=True, default=_uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kpi_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("kpis.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kpi_name: Mapped[str] = mapped_column(String(512), nullable=False)
    current_value: Mapped[str] = mapped_column(String(512), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    period: Mapped[str | None] = mapped_column(String(128), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trend: Mapped[str] = mapped_column(String(32), nullable=False)
    health: Mapped[str] = mapped_column(String(32), nullable=False)
    what_happened: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_happened: Mapped[str] = mapped_column(Text, nullable=False)
    business_impact: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risks: Mapped[list[Any]] = mapped_column(GenericJSON, nullable=False, default=list)
    opportunities: Mapped[list[Any]] = mapped_column(GenericJSON, nullable=False, default=list)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    forecast_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    forecast_horizon: Mapped[str | None] = mapped_column(String(128), nullable=True)
    forecast_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False, default="0.5")
    evidence_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="evidence")
    evidence_chunk_ids: Mapped[list[Any]] = mapped_column(GenericJSON, nullable=False, default=list)
    related_kpi_ids: Mapped[list[Any]] = mapped_column(GenericJSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExecutiveReportModel(Base):
    __tablename__ = "executive_reports"

    id: Mapped[uuid.UUID] = mapped_column(GenericUuid(as_uuid=True), primary_key=True, default=_uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        GenericUuid(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    health_score: Mapped[int] = mapped_column(Integer, nullable=False)
    health_label: Mapped[str] = mapped_column(String(32), nullable=False)
    timeline: Mapped[list[Any]] = mapped_column(GenericJSON, nullable=False, default=list)
    confidence: Mapped[str] = mapped_column(String(32), nullable=False, default="0.5")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
