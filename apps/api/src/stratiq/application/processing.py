"""Document processing pipeline use-case (called from ARQ worker)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from stratiq.application.ports import EmbeddingClient, LLMClient, ObjectStorage, VectorStore
from stratiq.domain.enums import DocumentStatus, KPIDomain
from stratiq.domain.exceptions import EvidenceRequiredError, ProcessingError

logger = logging.getLogger(__name__)

_DOMAIN_DETECT_PROMPT = """You are a domain classifier. Given the following document text (first 2000 chars), 
identify which strategic domains are present. Return a JSON object with key "domains" containing a list of 
domain strings from: financial, operational, strategic, risk, hr, marketing, technology, other.
Example: {"domains": ["financial", "operational"]}
Document text:
{text}"""

_KPI_EXTRACT_PROMPT = """You are a KPI extraction specialist. Given the following document chunks, 
extract all measurable KPIs. For each KPI return:
- name: descriptive KPI name
- value: numeric or textual value  
- unit: unit of measurement (optional)
- period: time period (optional)
- domain: one of financial/operational/strategic/risk/hr/marketing/technology/other
- evidence_chunk_ids: list of chunk IDs (strings) that contain evidence for this KPI

Return JSON: {"kpis": [{"name": ..., "value": ..., "unit": ..., "period": ..., "domain": ..., "evidence_chunk_ids": [...]}]}

Chunks (id: content):
{chunks}"""


class ProcessingService:
    def __init__(
        self,
        document_repo: "DocumentRepository",  # noqa: F821
        chunk_repo: "ChunkRepository",  # noqa: F821
        kpi_repo: "KPIRepository",  # noqa: F821
        storage: ObjectStorage,
        parser_factory: "ParserFactory",  # noqa: F821
        chunker: "SemanticChunker",  # noqa: F821
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
        llm_client: LLMClient,
        qdrant_collection: str,
        audit_service: "AuditService",  # noqa: F821
    ) -> None:
        self._docs = document_repo
        self._chunks = chunk_repo
        self._kpis = kpi_repo
        self._storage = storage
        self._parser_factory = parser_factory
        self._chunker = chunker
        self._embeddings = embedding_client
        self._vectors = vector_store
        self._llm = llm_client
        self._collection = qdrant_collection
        self._audit = audit_service

    async def process_document(self, document_id: uuid.UUID) -> None:
        from stratiq.domain.entities import Chunk, KPI

        logger.info("Processing document", extra={"doc_id": str(document_id)})
        doc = await self._docs.get_by_id(document_id)
        if doc is None:
            raise ProcessingError(f"Document {document_id} not found.")

        try:
            raw_bytes = await self._storage.load(doc.storage_path)
            parser = self._parser_factory.get_parser(doc.mime_type, doc.original_filename)
            markdown_text = parser.parse(raw_bytes)

            raw_chunks = self._chunker.chunk(markdown_text)

            now = datetime.now(UTC)
            chunk_entities: list[Chunk] = []
            for idx, raw_chunk in enumerate(raw_chunks):
                chunk = Chunk(
                    id=uuid.uuid4(),
                    document_id=document_id,
                    content=raw_chunk["content"],
                    chunk_index=idx,
                    page_number=raw_chunk.get("page_number"),
                    metadata=raw_chunk.get("metadata", {}),
                    created_at=now,
                )
                chunk_entities.append(chunk)

            await self._chunks.save_many(chunk_entities)

            texts = [c.content for c in chunk_entities]
            vectors = await self._embeddings.embed(texts)

            qdrant_points = [
                {
                    "id": str(chunk.id),
                    "vector": vec,
                    "payload": {
                        "document_id": str(document_id),
                        "owner_id": str(doc.owner_id),
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "page_number": chunk.page_number,
                    },
                }
                for chunk, vec in zip(chunk_entities, vectors)
            ]
            await self._vectors.upsert(self._collection, qdrant_points)

            # Domain detection
            preview_text = markdown_text[:2000]
            domain_result = await self._llm.json_completion(
                messages=[
                    {"role": "user", "content": _DOMAIN_DETECT_PROMPT.format(text=preview_text)}
                ],
                temperature=0.0,
                max_tokens=256,
            )
            detected_domains: list[str] = domain_result.get("domains", ["other"])

            # KPI extraction
            chunks_text = "\n".join(f"{c.id}: {c.content[:300]}" for c in chunk_entities[:40])
            kpi_result = await self._llm.json_completion(
                messages=[
                    {"role": "user", "content": _KPI_EXTRACT_PROMPT.format(chunks=chunks_text)}
                ],
                temperature=0.0,
                max_tokens=2048,
            )

            kpi_entities: list[KPI] = []
            for raw_kpi in kpi_result.get("kpis", []):
                evidence_ids = [uuid.UUID(cid) for cid in raw_kpi.get("evidence_chunk_ids", []) if cid]
                if not evidence_ids:
                    logger.warning("Skipping KPI with no evidence", extra={"kpi_name": raw_kpi.get("name")})
                    continue

                try:
                    kpi = KPI(
                        id=uuid.uuid4(),
                        document_id=document_id,
                        owner_id=doc.owner_id,
                        domain=KPIDomain(raw_kpi.get("domain", "other")),
                        name=raw_kpi.get("name", "Unknown"),
                        value=str(raw_kpi.get("value", "")),
                        unit=raw_kpi.get("unit"),
                        period=raw_kpi.get("period"),
                        evidence_chunk_ids=evidence_ids,
                        raw_extraction=raw_kpi,
                        created_at=now,
                        updated_at=now,
                    )
                    kpi_entities.append(kpi)
                except (ValueError, EvidenceRequiredError) as exc:
                    logger.warning("KPI validation failed: %s", exc)
                    continue

            if kpi_entities:
                await self._kpis.save_many(kpi_entities)

            await self._docs.update_status(document_id, DocumentStatus.ready)
            await self._audit.log_document_processed(doc.owner_id, document_id, len(kpi_entities))
            logger.info(
                "Document processed successfully",
                extra={"doc_id": str(document_id), "chunks": len(chunk_entities), "kpis": len(kpi_entities)},
            )

        except Exception as exc:
            logger.exception("Document processing failed", extra={"doc_id": str(document_id)})
            await self._docs.update_status(document_id, DocumentStatus.failed, error_message=str(exc))
            await self._audit.log_document_failed(doc.owner_id, document_id, str(exc))
            raise ProcessingError(str(exc)) from exc

    def _domain_for(self, raw: str) -> "KPIDomain":
        try:
            return KPIDomain(raw)
        except ValueError:
            return KPIDomain.other
