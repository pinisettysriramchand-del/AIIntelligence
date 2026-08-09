# MVP Traceability Matrix — StratIQ Part 4 (§27)

**Status:** COMPLETE (Stage 4J)  
**Date:** 2026-08-09  
**Mapping rule:** Product Requirement → Architecture Component → API/UI Module → Test → Acceptance Criterion

Deferred or partial items are marked **Partial** with an explicit gap. Future extensibility (§28) is listed as **Out of MVP scope**.

---

## Legend

| Status | Meaning |
|--------|---------|
| Met | MVP acceptance criterion satisfied with automated and/or documented evidence |
| Partial | Core path exists; known deferrals remain |
| Out | Explicitly future / non-MVP |

---

## Traceability rows

| ID | Product requirement | Architecture component | API / UI module | Test(s) | Acceptance criterion | Status | Stage |
|----|---------------------|------------------------|-----------------|---------|----------------------|--------|-------|
| **PR-18.1** | §18 PostgreSQL stores users, documents, jobs, KPIs, decisions, chat, audit | Postgres + Alembic (`001`–`007`); SQLAlchemy models/repos | Auth, documents, KPIs, decisions, chat, jobs APIs | `test_migration_di.py`, `test_auth_api.py`, `test_documents_api.py`, `test_decisions_api.py` | Migrations reach head; CRUD/read paths persist durable entities | Met | 4A, 4E, 4F |
| **PR-18.2** | §18 Organizations in transactional store | — | — | — | Multi-tenant orgs table/API | Out | — |
| **PR-18.3** | §18 Qdrant embeddings with metadata filters | `QdrantVectorStore`; chunk payload includes doc/owner | Chat RAG retrieval; processing upsert | `test_deferred_followups.py` (insufficient path); vector fakes in conftest | Chunks embeddable and retrievable scoped by owner | Met | Part 3 / ADR-003 |
| **PR-18.4** | §18 Object storage for uploads/reports | `LocalFileStorage` / Compose `storage_data` | `POST /documents`, `GET /reports/executive.pdf` | `test_documents_api.py`, decisions PDF integration | Upload bytes and PDF export stored outside DB | Met | Part 2–3 |
| **PR-19** | §19 Flow: Source → … → Decision Card → Dashboard | Processing pipeline + DI service + dashboard | Upload → process → generate DI → dashboard/decisions UI | Integration auth/docs/decisions; `test_ui_l1_l2_l3.py` | End-to-end journey completable for a logged-in user | Met | 4H |
| **PR-20.1** | §20 Idempotent processing | `ProcessingService` purge + job idempotency | `POST /documents/{id}/process` | `test_processing_jobs.py`, `test_documents_api.py` | Re-enqueue while active returns same job; reprocess replaces artifacts | Met | 4E |
| **PR-20.2** | §20 Retry policies + dead-letter | ARQ `Retry` + `processing_jobs.dead_letter` + Redis DLQ | `GET /documents/jobs/dead-letter` | `test_processing_jobs.py` | Exhausted attempts mark dead_letter; DLQ payload recorded | Met | 4E |
| **PR-20.3** | §20 Health checks | FastAPI `/health`; Compose healthchecks | `GET /health` | App factory health route | Health endpoint returns ok when process up | Met | Part 1 |
| **PR-20.4** | §20 Backups + graceful degradation | DR runbook + backup scripts; Redis rebuildable | Ops scripts (not runtime API) | `test_dr_runbook.py` | Documented RPO/RTO + runnable backup/restore scripts | Met | 4G |
| **PR-21** | §21 DR: Postgres backups, storage versioning, config backup, RPO/RTO | `docs/ops/DR_RUNBOOK.md`; `scripts/backup-*` | Operator runbook | `test_dr_runbook.py` | RPO/RTO table + restore procedure documented | Met | 4G |
| **PR-22.1** | §22 Logs, metrics, traces | Process `/metrics`; OTEL optional (ADR-006) | `GET /metrics`; OTEL exporters | `test_metrics.py`, `test_otel.py` | Metrics snapshot available; OTEL enableable via config | Met | Part 3 / ADR-006 |
| **PR-22.2** | §22 Correlate request / job / AI | Correlation middleware + job `correlation_id` + AI spans | `X-Request-ID`; processing jobs; LLM spans | `test_correlation.py`, documents process correlation test | Request id echoes; job stores correlation; AI span attrs set | Met | 4F |
| **PR-24.1** | §24 KPI name, meaning, value, unit, period | `KPI` entity + ORM; extraction prompt `kpi.extract` | `GET /kpis`, dashboard Top KPIs | `test_kpi_intelligence.py` | Extracted KPI persists meaning/value/unit/period when present | Met | 4B |
| **PR-24.2** | §24 Current vs prior, trend, confidence, dimensions | `kpi_intelligence.py` deterministic compare | KPI API `comparison` / `trend` / `confidence` | `test_kpi_intelligence.py` | Numeric prior compare yields trend/delta when parseable | Met | 4B |
| **PR-24.3** | §24 Source evidence | `evidence_chunk_ids`; evidence endpoint | `GET /kpis/{id}/evidence` | `test_kpi_evidence.py` | KPI without evidence rejected; evidence listable | Met | Part 3 |
| **PR-24.4** | §24 Deterministic calc when source permits | Prior-period enrichment (not full calc engine) | Processing + KPI schemas | `test_kpi_intelligence.py` | Deterministic path used for numeric period compare | Partial | 4B (full definition/observation split deferred) |
| **PR-25.1** | §25 Decision Card fields 1–11 | `DecisionCard` + migration `005`; DI prompt | `GET /decisions/cards`, `/cards/{id}`; UI decisions | `test_decision_card_validation.py`, `test_decisions_api.py` | Cards expose topic, signal, narratives, risks/opps, recommendation, expected_outcome, confidence | Met | 4D |
| **PR-25.2** | §25 Recommendations are decision support only | Prompt + product copy; no execute APIs | Decision UI; generate endpoint | Prompt registry evidence rules | No autonomous action execution endpoints | Met | 4D / 4I |
| **PR-26** | §26 DQ: missing/duplicate/units/periods/conflicts/history + visible | `data_quality.py`; `documents.quality_warnings` | Dashboard DQ panel; upload warnings | `test_data_quality.py` | Warnings detected and returned on dashboard/documents | Met | 4C |
| **PR-27** | §27 Traceability matrix | This document | `docs/MVP_TRACEABILITY_MATRIX.md` | `test_mvp_traceability.py` | Every major MVP capability maps PR→Arch→API/UI→Test→AC | Met | 4J |
| **PR-28** | §28 Future extensibility hooks | Ports (`LLMClient`, `TaskQueue`, `VectorStore`); Clean Architecture | N/A (design) | ADR-001–007 | New connectors/models can plug ports without rewriting domain | Out (design readiness only) | — |
| **PR-UI.1** | Part 4 UI L1 Executive Signal | Dashboard L1 panel + `HealthMeter` | `/dashboard` | `test_ui_l1_l2_l3.py` | L1 shows health, primary KPI, major risk/opportunity | Met | 4H |
| **PR-UI.2** | Part 4 UI L2 Explanation + charts | SparkLine / RankedBarChart | `/dashboard`, `/decisions/[id]` | `test_ui_l1_l2_l3.py` | L2 shows trends/composition/drivers | Met | 4H |
| **PR-UI.3** | Part 4 UI L3 Action | Decision cards + next step | `/dashboard` L3, `/decisions/*` | `test_ui_l1_l2_l3.py` | L3 shows recommendation + expected outcome | Met | 4H |
| **PR-AI.1** | Prompt governance (id/version/schemas/evals) | `prompt_registry.py`; ADR-007 | `GET /api/v1/ai/prompts` | `test_prompt_registry.py` | All production prompts registered; required eval scenarios covered | Met | 4I |
| **PR-AI.2** | Model provider abstraction | `LLMClient` / `EmbeddingClient` ports | DI via deps | Port usage in services | Services call ports, not vendor SDKs directly | Met | Part 3 / 4I |
| **PR-CORE.1** | Auth register/login/refresh/logout | JWT + Redis refresh/blacklist | `/api/v1/auth/*`, `/login` | `test_auth_api.py`, `test_security.py` | User can register, login, refresh, logout | Met | Part 1 |
| **PR-CORE.2** | Document upload + process | Parser/chunker/embed/KPI pipeline | `/documents`, `/upload` | `test_documents_api.py`, parsers/chunking unit tests | Upload accepted types; process enqueues job | Met | Part 1 / 4E |
| **PR-CORE.3** | RAG chat with citations / insufficient evidence | ChatService + Qdrant + `rag.chat` prompt | `/chat`, chat sessions API | `test_deferred_followups.py` | Empty retrieval returns insufficient-evidence without LLM invent | Met | Part 3 |
| **PR-CORE.4** | Executive PDF export | `pdf_export.py` | `GET /reports/executive.pdf`, `/reports` | `test_decisions_api.py` | PDF bytes returned with `%PDF` header | Met | Part 2 |

---

## Coverage summary

| Bucket | Met | Partial | Out |
|--------|-----|---------|-----|
| Enterprise data / flow / reliability / DR / observability | 10 | 0 | 1 (orgs) |
| KPI / Decision / DQ / Traceability | 8 | 1 | 0 |
| UI / AI governance / core journey | 9 | 0 | 1 (§28 future) |

---

## Known gaps (frozen at Part 4 acceptance)

These are **frozen deferrals** (`FD-4.x` in `docs/PART4_ACCEPTANCE.md`). Do not treat as open Part 4 work.

1. **Org multi-tenancy** (FD-4.1)  
2. **Full KPI definition vs observation model + tabular calc engine** (FD-4.2)  
3. **Raw row-level DQ scan** (FD-4.3)  
4. **Live LLM eval harness / W3C traceparent across queue** (FD-4.4, FD-4.5)  
5. **Off-site WAL / multi-AZ DR** (FD-4.6)  
6. **DLQ replay UI / interactive chart filters / §28 futures** (FD-4.7–FD-4.9)

---

## How to maintain

1. New MVP capability → add a row with a new `PR-*` id.  
2. Link the primary automated test path (prefer unit/integration already in CI).  
3. Update acceptance criterion to something falsifiable.  
4. Keep Stage column aligned with `docs/STAGE4*_VERIFICATION.md` when Part 4-scoped.
