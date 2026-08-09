# 02_ARCHITECTURE.md — Part 3

## 13. AI Intelligence Architecture
Business Evidence → Document Intelligence → Domain Intelligence → KPI Intelligence → Decision Intelligence → Executive Intelligence.

The MVP uses a modular orchestration layer. Each capability must be independently testable and may later become a LangGraph workflow or separate agent.

## 14. RAG Architecture
1. Parse source
2. Normalize content
3. Chunk semantically
4. Generate embeddings
5. Store vectors
6. Retrieve evidence
7. Rerank when required
8. Assemble context
9. Generate answer
10. Attach citations

RAG must not invent facts when evidence is unavailable.

## 15. Data Flow
Upload → Object Storage → Processing Worker → PostgreSQL metadata → Vector Store → AI Services → Dashboard.

## 16. Observability
Capture API latency, processing duration, AI latency, token usage, retrieval quality, error rates, failed documents and audit events.

## 17. Architecture Decision Records
ADR-001 FastAPI backend. ADR-002 PostgreSQL transactional data. ADR-003 Qdrant vector retrieval. ADR-004 Redis caching/transient state. ADR-005 Docker reproducible deployment. Each ADR records context, decision, alternatives and consequences.
