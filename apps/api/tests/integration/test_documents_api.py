"""Integration tests for the documents API endpoints."""

from __future__ import annotations

import io
import uuid

import openpyxl
import pytest
from httpx import AsyncClient


def _make_pdf_bytes() -> bytes:
    return b"%PDF-1.4 placeholder pdf content for testing"


def _make_xlsx_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Company", "Revenue", "Growth"])
    ws.append(["ACME Corp", 1000000, "15%"])
    ws.append(["Beta Ltd", 500000, "8%"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestDocumentUpload:
    @pytest.mark.asyncio
    async def test_upload_csv_success(self, auth_client):
        client, headers = auth_client
        csv_data = b"Name,Revenue\nACME,1000000\nBeta,500000"
        response = await client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": ("report.csv", csv_data, "text/csv")},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "report.csv"
        assert data["status"] == "uploaded"
        assert data["size_bytes"] == len(csv_data)

    @pytest.mark.asyncio
    async def test_upload_xlsx_success(self, auth_client):
        client, headers = auth_client
        xlsx_data = _make_xlsx_bytes()
        response = await client.post(
            "/api/v1/documents",
            headers=headers,
            files={
                "file": (
                    "financials.xlsx",
                    xlsx_data,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_upload_unsupported_type_rejected(self, auth_client):
        client, headers = auth_client
        response = await client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": ("script.js", b"console.log('hi')", "text/javascript")},
        )
        assert response.status_code == 415

    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/documents",
            files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
        )
        assert response.status_code == 401


class TestDocumentList:
    @pytest.mark.asyncio
    async def test_list_empty_initially(self, auth_client):
        client, headers = auth_client
        response = await client.get("/api/v1/documents", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_shows_uploaded_document(self, auth_client):
        client, headers = auth_client
        csv_data = b"col1,col2\nval1,val2"
        await client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
        response = await client.get("/api/v1/documents", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/documents")
        assert response.status_code == 401


class TestDocumentGet:
    @pytest.mark.asyncio
    async def test_get_own_document(self, auth_client):
        client, headers = auth_client
        csv_data = b"a,b\n1,2"
        upload = await client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": ("get_test.csv", csv_data, "text/csv")},
        )
        doc_id = upload.json()["id"]

        response = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == doc_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_404(self, auth_client):
        client, headers = auth_client
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/documents/{fake_id}", headers=headers)
        assert response.status_code == 404


class TestDocumentProcess:
    @pytest.mark.asyncio
    async def test_process_enqueues_job(self, auth_client):
        client, headers = auth_client
        csv_data = b"metric,value\nrevenue,1000"
        upload = await client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": ("kpis.csv", csv_data, "text/csv")},
        )
        assert upload.status_code == 201
        doc_id = upload.json()["id"]

        response = await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["document_id"] == doc_id
        assert body["status"] == "queued"
        assert body["max_attempts"] >= 1
        assert "process:" in body["idempotency_key"]

        again = await client.post(f"/api/v1/documents/{doc_id}/process", headers=headers)
        assert again.status_code == 200
        assert again.json()["id"] == body["id"]

        jobs = await client.get(f"/api/v1/documents/{doc_id}/jobs", headers=headers)
        assert jobs.status_code == 200
        assert jobs.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_process_nonexistent_returns_404(self, auth_client):
        client, headers = auth_client
        fake_id = str(uuid.uuid4())
        response = await client.post(f"/api/v1/documents/{fake_id}/process", headers=headers)
        assert response.status_code == 404


class TestDocumentDelete:
    @pytest.mark.asyncio
    async def test_delete_own_document(self, auth_client):
        client, headers = auth_client
        csv_data = b"x,y\n1,2"
        upload = await client.post(
            "/api/v1/documents",
            headers=headers,
            files={"file": ("del.csv", csv_data, "text/csv")},
        )
        doc_id = upload.json()["id"]

        delete_response = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
        assert delete_response.status_code == 200

        get_response = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, auth_client):
        client, headers = auth_client
        fake_id = str(uuid.uuid4())
        response = await client.delete(f"/api/v1/documents/{fake_id}", headers=headers)
        assert response.status_code == 404
