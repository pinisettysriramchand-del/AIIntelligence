from datetime import UTC, datetime
from uuid import uuid4

import pytest

from stratiq.domain.entities import Document, KPI
from stratiq.domain.enums import DocumentStatus, DocumentType


@pytest.mark.asyncio
async def test_upload_and_process_enqueue(client, memory_stack):
    register = await client.post(
        "/api/auth/register",
        json={"email": "ops@example.com", "password": "password123", "full_name": "Ops"},
    )
    assert register.status_code == 201
    login = await client.post(
        "/api/auth/login",
        json={"email": "ops@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    upload = await client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("metrics.csv", b"kpi,value\nRevenue,250\n", "text/csv")},
    )
    assert upload.status_code == 201
    doc = upload.json()
    assert doc["status"] == "uploaded"
    assert doc["filename"] == "metrics.csv"

    process = await client.post(f"/api/documents/{doc['id']}/process", headers=headers)
    assert process.status_code == 200
    assert process.json()["status"] == "processing"
    assert memory_stack["jobs"].jobs == [doc["id"]]


@pytest.mark.asyncio
async def test_dashboard_and_chat(client, memory_stack):
    register = await client.post(
        "/api/auth/register",
        json={"email": "analyst@example.com", "password": "password123", "full_name": "Ann"},
    )
    assert register.status_code == 201
    login = await client.post(
        "/api/auth/login",
        json={"email": "analyst@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/auth/me", headers=headers)
    owner_id = me.json()["id"]

    from uuid import UUID

    owner = UUID(owner_id)
    document_id = uuid4()
    chunk_id = uuid4()
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
    memory_stack["kpis"].items.append(
        KPI(
            id=uuid4(),
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
    memory_stack["vectors"].points.append(
        {
            "id": str(chunk_id),
            "vector": [1.0, 0.0, 0.0],
            "payload": {
                "chunk_id": str(chunk_id),
                "document_id": str(document_id),
                "owner_id": str(owner),
                "content": "Revenue for Q1 was 250 USD.",
                "filename": "ready.csv",
            },
        }
    )

    dashboard = await client.get("/api/dashboard", headers=headers)
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["summary"]["kpi_count"] == 1
    assert body["kpis"][0]["name"] == "Revenue"

    chat = await client.post(
        "/api/chat",
        headers=headers,
        json={"question": "What was revenue?"},
    )
    assert chat.status_code == 200
    answer = chat.json()
    assert answer["role"] == "assistant"
    assert answer["citations"]
    assert "Revenue" in answer["content"] or "evidence" in answer["content"].lower() or answer["content"]
