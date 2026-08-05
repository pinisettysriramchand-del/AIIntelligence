from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from stratiq.application.health import compute_health_score
from stratiq.domain.entities import Chunk, DecisionCard, Document, KPI
from stratiq.domain.enums import DocumentStatus, DocumentType, HealthLabel


def test_compute_health_score_labels():
    cards = [
        DecisionCard(
            id=uuid4(),
            owner_id=uuid4(),
            kpi_id=uuid4(),
            document_id=uuid4(),
            kpi_name="Revenue",
            current_value="100",
            unit="USD",
            period="Q1",
            domain="Retail",
            trend="up",
            health=HealthLabel.HEALTHY,
            what_happened="x",
            why_it_happened="y",
            risks=[],
            opportunities=[],
            recommendation="z",
            forecast_value="110",
            forecast_horizon="Q2",
            forecast_explanation="growth",
            evidence_chunk_ids=["a"],
        )
    ]
    score, label = compute_health_score(cards, ready_documents=2, failed_documents=0, llm_score=80)
    assert 0 <= score <= 100
    assert label in {HealthLabel.HEALTHY, HealthLabel.WATCH, HealthLabel.CRITICAL}


@pytest.mark.asyncio
async def test_generate_decisions_and_pdf(client, memory_stack):
    register = await client.post(
        "/api/auth/register",
        json={"email": "di@example.com", "password": "password123", "full_name": "DI User"},
    )
    assert register.status_code == 201
    login = await client.post(
        "/api/auth/login",
        json={"email": "di@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/auth/me", headers=headers)
    owner = UUID(me.json()["id"])

    document_id = uuid4()
    chunk_id = uuid4()
    kpi_id = uuid4()
    memory_stack["documents"].items[document_id] = Document(
        id=document_id,
        owner_id=owner,
        filename="ready.csv",
        content_type="text/csv",
        storage_key="x",
        status=DocumentStatus.READY,
        document_type=DocumentType.CSV,
        domain="Retail",
        domain_confidence=0.8,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    memory_stack["chunks"].items[document_id] = [
        Chunk(
            id=chunk_id,
            document_id=document_id,
            ordinal=0,
            content="Revenue for Q1 was 250 USD.",
            token_estimate=8,
        )
    ]
    memory_stack["kpis"].items.append(
        KPI(
            id=kpi_id,
            document_id=document_id,
            owner_id=owner,
            name="Revenue",
            value="250",
            unit="USD",
            period="Q1",
            evidence_chunk_ids=[str(chunk_id)],
            domain="Retail",
        )
    )

    generated = await client.post("/api/decisions/generate", headers=headers, json={})
    assert generated.status_code == 201, generated.text
    body = generated.json()
    assert body["report"]["health_score"] >= 0
    assert body["cards"]
    assert body["cards"][0]["recommendation"]

    cards = await client.get("/api/decisions/cards", headers=headers)
    assert cards.status_code == 200
    assert len(cards.json()) >= 1

    executive = await client.get("/api/decisions/executive", headers=headers)
    assert executive.status_code == 200
    assert executive.json()["summary"]

    forecasts = await client.get("/api/forecasts", headers=headers)
    assert forecasts.status_code == 200
    assert forecasts.json()

    pdf = await client.get("/api/reports/executive.pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"

    dashboard = await client.get("/api/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["summary"]["decision_card_count"] >= 1
    assert dashboard.json()["executive_summary"]
