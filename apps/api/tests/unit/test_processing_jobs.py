"""Stage 4E: processing job reliability helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from stratiq.application.documents import DocumentService
from stratiq.domain.entities import Document, ProcessingJob
from stratiq.domain.enums import DocumentStatus, ProcessingJobStatus


class _DocRepo:
    def __init__(self, doc: Document) -> None:
        self.doc = doc
        self.status_updates: list[tuple] = []

    async def get_by_id(self, doc_id):
        return self.doc if self.doc.id == doc_id else None

    async def update_status(self, doc_id, status, error_message=None, quality_warnings=None):
        self.status_updates.append((doc_id, status, error_message))
        self.doc.status = status


class _JobRepo:
    def __init__(self) -> None:
        self.jobs: dict = {}
        self.active: ProcessingJob | None = None

    async def get_active_for_document(self, document_id):
        if self.active and self.active.document_id == document_id:
            return self.active
        return None

    async def save(self, job: ProcessingJob) -> ProcessingJob:
        self.jobs[job.id] = job
        self.active = job
        return job

    async def update(self, job_id, **kwargs):
        job = self.jobs[job_id]
        if "arq_job_id" in kwargs and kwargs["arq_job_id"] is not None:
            job.arq_job_id = kwargs["arq_job_id"]


class _Queue:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def enqueue(self, function_name: str, **kwargs):
        self.calls.append({"function": function_name, **kwargs})
        return kwargs.get("_job_id") or "arq-1"


class _Audit:
    async def log_document_uploaded(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_enqueue_reuses_active_job():
    now = datetime.now(UTC)
    owner_id = uuid4()
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        owner_id=owner_id,
        filename="a.csv",
        original_filename="a.csv",
        mime_type="text/csv",
        size_bytes=10,
        storage_path="x",
        status=DocumentStatus.uploaded,
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    jobs = _JobRepo()
    queue = _Queue()
    svc = DocumentService(_DocRepo(doc), storage=None, task_queue=queue, audit_service=_Audit(), job_repo=jobs, max_attempts=3)

    first = await svc.enqueue_processing(doc_id, owner_id)
    second = await svc.enqueue_processing(doc_id, owner_id)

    assert first.id == second.id
    assert len(queue.calls) == 1
    assert queue.calls[0]["function"] == "process_document"
    assert queue.calls[0]["processing_job_id"] == str(first.id)
    assert queue.calls[0]["correlation_id"]
    assert first.correlation_id == queue.calls[0]["correlation_id"]


def test_retry_policy_boundaries():
    assert ProcessingJobStatus.dead_letter.value == "dead_letter"
    assert ProcessingJobStatus.queued.value == "queued"
