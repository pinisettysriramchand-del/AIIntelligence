"""Unit tests for deferred Part 3 follow-ups (chat, forecasts, dashboard comparisons)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from stratiq.application.chat import ChatService, _INSUFFICIENT_EVIDENCE_REPLY
from stratiq.application.dashboard import DashboardService
from stratiq.application.decisions import DecisionIntelligenceService
from stratiq.domain.entities import ChatSession, KPI
from stratiq.domain.enums import EvidenceMode, KPIDomain, TrendDirection


@pytest.mark.asyncio
async def test_chat_insufficient_evidence_skips_llm():
    owner_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(UTC)
    session = ChatSession(
        id=session_id,
        owner_id=owner_id,
        title="t",
        created_at=now,
        updated_at=now,
    )

    sessions = AsyncMock()
    sessions.get_by_id.return_value = session
    messages = AsyncMock()
    messages.list_by_session.return_value = []
    chunks = AsyncMock()
    embeddings = AsyncMock()
    embeddings.embed_one.return_value = [0.1, 0.2]
    vectors = AsyncMock()
    vectors.search.return_value = []
    llm = AsyncMock()
    audit = AsyncMock()

    svc = ChatService(
        session_repo=sessions,
        message_repo=messages,
        chunk_repo=chunks,
        embedding_client=embeddings,
        vector_store=vectors,
        llm_client=llm,
        qdrant_collection="test",
        audit_service=audit,
    )

    reply = await svc.post_message(session_id, owner_id, "What is revenue?")
    assert reply.content == _INSUFFICIENT_EVIDENCE_REPLY
    assert reply.citations == []
    llm.chat_completion.assert_not_called()


def test_dashboard_builds_period_comparison():
    owner = uuid.uuid4()
    doc = uuid.uuid4()
    now = datetime.now(UTC)
    chunk = uuid.uuid4()
    k1 = KPI(
        id=uuid.uuid4(),
        document_id=doc,
        owner_id=owner,
        name="Revenue",
        value="100",
        unit="USD",
        period="2024-Q1",
        domain=KPIDomain.financial,
        evidence_chunk_ids=[chunk],
        raw_extraction={},
        created_at=now,
        updated_at=now,
    )
    k2 = KPI(
        id=uuid.uuid4(),
        document_id=doc,
        owner_id=owner,
        name="Revenue",
        value="120",
        unit="USD",
        period="2024-Q2",
        domain=KPIDomain.financial,
        evidence_chunk_ids=[chunk],
        raw_extraction={},
        created_at=now,
        updated_at=now,
    )
    comparisons = DashboardService._build_comparisons([k1, k2])
    assert k1.id not in comparisons
    assert comparisons[k2.id]["trend"] == "up"
    assert comparisons[k2.id]["previous_value"] == "100"
    assert comparisons[k2.id]["delta_label"].startswith("+")


@pytest.mark.asyncio
async def test_list_forecasts_marks_insufficient_history():
    owner = uuid.uuid4()
    card = SimpleNamespace(
        kpi_id=uuid.uuid4(),
        kpi_name="Revenue",
        current_value="100",
        unit="USD",
        forecast_value=None,
        forecast_horizon=None,
        forecast_explanation=None,
        trend=TrendDirection.flat,
        confidence=0.4,
        evidence_mode=EvidenceMode.insufficient,
    )
    decisions = AsyncMock()
    decisions.list_cards.return_value = [card]
    svc = DecisionIntelligenceService(
        kpi_repo=AsyncMock(),
        doc_repo=AsyncMock(),
        chunk_repo=AsyncMock(),
        decision_repo=decisions,
        llm=AsyncMock(),
        audit=AsyncMock(),
    )
    items = await svc.list_forecasts(owner)
    assert len(items) == 1
    assert items[0]["status"] == "insufficient_history"
    assert "Insufficient historical data" in items[0]["forecast_explanation"]
