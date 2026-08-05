from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from stratiq.application.ports import (
    AuditRepository,
    ChunkRepository,
    DecisionRepository,
    DocumentParser,
    DocumentRepository,
    EmbeddingsPort,
    KPIRepository,
    LLMPort,
    ObjectStorage,
    VectorStore,
)
from stratiq.application.decisions import DecisionIntelligenceService
from stratiq.domain.entities import Chunk, KPI
from stratiq.domain.enums import AuditAction, DocumentStatus
from stratiq.domain.exceptions import NotFoundError, ProcessingError, ValidationError
from stratiq.infrastructure.ai import prompts
from stratiq.infrastructure.chunking.semantic import chunk_markdown
from stratiq.infrastructure.parsers.factory import get_parser

logger = logging.getLogger(__name__)


def validate_kpi_payload(raw: dict[str, Any], known_chunk_ids: set[str]) -> None:
    name = (raw.get("name") or "").strip()
    value = str(raw.get("value", "")).strip()
    evidence = raw.get("evidence_chunk_ids") or []
    if not name or not value:
        raise ValidationError("KPI requires name and value")
    if not isinstance(evidence, list) or not evidence:
        raise ValidationError(f"KPI '{name}' missing evidence_chunk_ids")
    evidence_ids = [str(e) for e in evidence]
    if not any(eid in known_chunk_ids for eid in evidence_ids):
        raise ValidationError(f"KPI '{name}' evidence does not match document chunks")


class DocumentProcessingService:
    def __init__(
        self,
        documents: DocumentRepository,
        chunks: ChunkRepository,
        kpis: KPIRepository,
        storage: ObjectStorage,
        embeddings: EmbeddingsPort,
        llm: LLMPort,
        vectors: VectorStore,
        audit: AuditRepository,
        embedding_dimensions: int,
        decisions: DecisionRepository | None = None,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._kpis = kpis
        self._storage = storage
        self._embeddings = embeddings
        self._llm = llm
        self._vectors = vectors
        self._audit = audit
        self._embedding_dimensions = embedding_dimensions
        self._decisions = decisions

    async def process(self, document_id: UUID) -> None:
        document = await self._documents.get_by_id(document_id)
        if not document:
            raise NotFoundError(f"Document {document_id} not found")

        try:
            data = await self._storage.get(document.storage_key)
            parser: DocumentParser = get_parser(document.filename, document.content_type)
            markdown = parser.parse(data, document.filename)
            if not markdown.strip():
                raise ProcessingError("Parser produced empty content")

            text_chunks = chunk_markdown(markdown)
            if not text_chunks:
                raise ProcessingError("No chunks produced from document")

            chunk_entities: list[Chunk] = []
            for ordinal, text in enumerate(text_chunks):
                chunk_entities.append(
                    Chunk(
                        id=uuid4(),
                        document_id=document.id,
                        ordinal=ordinal,
                        content=text,
                        token_estimate=max(1, len(text.split())),
                        metadata={"filename": document.filename},
                    )
                )
            saved_chunks = await self._chunks.replace_for_document(document.id, chunk_entities)
            vectors = await self._embeddings.embed([c.content for c in saved_chunks])
            await self._vectors.ensure_collection(self._embedding_dimensions)
            await self._vectors.delete_document(str(document.id))
            points = []
            for chunk, vector in zip(saved_chunks, vectors, strict=True):
                points.append(
                    {
                        "id": str(chunk.id),
                        "vector": vector,
                        "payload": {
                            "chunk_id": str(chunk.id),
                            "document_id": str(document.id),
                            "owner_id": str(document.owner_id),
                            "ordinal": chunk.ordinal,
                            "content": chunk.content,
                            "filename": document.filename,
                        },
                    }
                )
            await self._vectors.upsert_chunks(points)

            known_ids = {str(c.id) for c in saved_chunks}
            sample = "\n\n".join(
                f"[chunk:{c.id}]\n{c.content}" for c in saved_chunks[:12]
            )
            domain_raw = await self._llm.complete_json(
                prompts.DOMAIN_DETECTION_SYSTEM,
                prompts.domain_detection_user(sample),
            )
            domain = str(domain_raw.get("industry") or domain_raw.get("domain") or "General")
            confidence = float(domain_raw.get("confidence") or 0.0)

            kpi_raw = await self._llm.complete_json(
                prompts.KPI_DISCOVERY_SYSTEM,
                prompts.kpi_discovery_user(domain, sample),
            )
            items = kpi_raw.get("kpis") if isinstance(kpi_raw, dict) else None
            if not isinstance(items, list):
                raise ProcessingError("KPI discovery returned invalid payload")

            kpi_entities: list[KPI] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                try:
                    validate_kpi_payload(item, known_ids)
                except ValidationError as exc:
                    logger.warning("skipping_invalid_kpi reason=%s", exc)
                    continue
                evidence = [str(e) for e in item["evidence_chunk_ids"] if str(e) in known_ids]
                if not evidence:
                    continue
                kpi_entities.append(
                    KPI(
                        id=uuid4(),
                        document_id=document.id,
                        owner_id=document.owner_id,
                        name=str(item["name"]).strip(),
                        value=str(item["value"]).strip(),
                        unit=(str(item["unit"]).strip() if item.get("unit") else None),
                        period=(str(item["period"]).strip() if item.get("period") else None),
                        evidence_chunk_ids=evidence,
                        domain=domain,
                        raw=item,
                    )
                )

            await self._kpis.replace_for_document(document.id, kpi_entities)
            document.status = DocumentStatus.READY
            document.domain = domain
            document.domain_confidence = confidence
            document.error_message = None
            await self._documents.update(document)
            await self._audit.record(
                AuditAction.DOCUMENT_PROCESS_COMPLETED,
                document.owner_id,
                "document",
                str(document.id),
                {"kpi_count": len(kpi_entities), "chunk_count": len(saved_chunks)},
            )
            if self._decisions is not None and kpi_entities:
                try:
                    di = DecisionIntelligenceService(
                        kpis=self._kpis,
                        documents=self._documents,
                        chunks=self._chunks,
                        decisions=self._decisions,
                        llm=self._llm,
                        audit=self._audit,
                    )
                    await di.generate(document.owner_id, document.id)
                except Exception:
                    logger.exception("decision_intelligence_failed document_id=%s", document.id)
            logger.info(
                "document_processed id=%s kpis=%s chunks=%s",
                document.id,
                len(kpi_entities),
                len(saved_chunks),
            )
        except Exception as exc:
            logger.exception("document_process_failed id=%s", document_id)
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)[:2000]
            await self._documents.update(document)
            await self._audit.record(
                AuditAction.DOCUMENT_PROCESS_FAILED,
                document.owner_id,
                "document",
                str(document.id),
                {"error": str(exc)[:500]},
            )
            raise ProcessingError(str(exc)) from exc
