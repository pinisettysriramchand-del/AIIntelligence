"""Integration tests for Decision Intelligence APIs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from stratiq.domain.entities import Chunk, KPI
from stratiq.domain.enums import DocumentStatus, KPIDomain
from stratiq.infrastructure.db.repositories import ChunkRepository, DocumentRepository, KPIRepository
from stratiq.interface.deps import get_llm


@pytest.mark.asyncio
async def test_generate_decisions_and_pdf(
    client: AsyncClient,
    app,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
    current_user_id: uuid.UUID,
):
    # Seed a ready document + KPI + evidence chunk
    from stratiq.domain.entities import Document

    now = datetime.now(UTC)
    document_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    kpi_id = uuid.uuid4()

    doc_repo = DocumentRepository(db_session)
    chunk_repo = ChunkRepository(db_session)
    kpi_repo = KPIRepository(db_session)

    await doc_repo.save(
        Document(
            id=document_id,
            owner_id=current_user_id,
            filename="ready.csv",
            original_filename="ready.csv",
            mime_type="text/csv",
            size_bytes=32,
            storage_path="x",
            status=DocumentStatus.ready,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
    )
    await chunk_repo.save_many(
        [
            Chunk(
                id=chunk_id,
                document_id=document_id,
                content="Revenue for Q1 was 250 USD.",
                chunk_index=0,
                page_number=None,
                metadata={},
                created_at=now,
            )
        ]
    )
    await kpi_repo.save_many(
        [
            KPI(
                id=kpi_id,
                document_id=document_id,
                owner_id=current_user_id,
                domain=KPIDomain.financial,
                name="Revenue",
                value="250",
                unit="USD",
                period="Q1",
                evidence_chunk_ids=[chunk_id],
                raw_extraction={},
                created_at=now,
                updated_at=now,
            )
        ]
    )
    await db_session.commit()

    class _DILlm:
        async def chat_completion(self, messages, temperature=0.7, max_tokens=1024) -> str:
            return "ok"

        async def json_completion(self, messages, temperature=0.0, max_tokens=1024) -> dict:
            return {
                "executive_summary": "Revenue is stable with actionable upside.",
                "health_score": 78,
                "confidence": 0.82,
                "timeline": [
                    {
                        "title": "Revenue review",
                        "detail": "Revenue held at target.",
                        "severity": "medium",
                    }
                ],
                "cards": [
                    {
                        "kpi_id": str(kpi_id),
                        "kpi_name": "Revenue",
                        "trend": "up",
                        "health": "healthy",
                        "what_happened": "Revenue reached 250 USD in Q1.",
                        "why_it_happened": "Demand held and pricing remained stable.",
                        "business_impact": "Supports cash flow and growth investment.",
                        "risks": ["Margin compression if input costs rise"],
                        "opportunities": ["Expand top-performing channels"],
                        "recommendation": "Protect pricing discipline and scale winning channels.",
                        "forecast_value": "260",
                        "forecast_horizon": "next quarter",
                        "forecast_explanation": "Continuation of current demand trajectory.",
                        "confidence": 0.85,
                        "evidence_mode": "evidence",
                        "evidence_chunk_ids": [str(chunk_id)],
                        "related_kpi_ids": [],
                    }
                ],
            }

    app.dependency_overrides[get_llm] = lambda: _DILlm()

    generated = await client.post(
        "/api/v1/decisions/generate",
        headers=auth_headers,
        json={},
    )
    assert generated.status_code == 201, generated.text
    body = generated.json()
    assert body["report"]["health_score"] >= 0
    assert body["report"]["confidence"] > 0
    assert body["cards"]
    assert body["cards"][0]["business_impact"]
    assert body["cards"][0]["evidence_mode"] == "evidence"
    assert body["cards"][0]["confidence"] > 0
    assert body["cards"][0]["topic"] == "Decision on Revenue"
    assert body["cards"][0]["expected_outcome"] == "Outcome not specified from evidence."
    assert "Revenue:" in body["cards"][0]["kpi_signal"]
    assert "up" in body["cards"][0]["kpi_signal"]
    assert "healthy" in body["cards"][0]["kpi_signal"]

    cards = await client.get("/api/v1/decisions/cards", headers=auth_headers)
    assert cards.status_code == 200
    assert len(cards.json()) >= 1

    executive = await client.get("/api/v1/decisions/executive", headers=auth_headers)
    assert executive.status_code == 200
    assert executive.json()["summary"]

    forecasts = await client.get("/api/v1/forecasts", headers=auth_headers)
    assert forecasts.status_code == 200
    assert forecasts.json()

    pdf = await client.get("/api/v1/reports/executive.pdf", headers=auth_headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"
