# StratIQ Architecture Validation

**Status:** APPROVED  
**Date:** 2026-08-05  
**Sources:** `01_PRODUCT_REQUIREMENTS`, `02_ARCHITECTURE`, `03_IMPLEMENTATION_GUIDE`, `05_CURSOR_RULES`

---

## Verdict

**PASS.** Decisions D1–D4 approved. Stage 1 implementation authorized and delivered (see `STAGE1_STATUS.md`).

---

## Coverage Matrix

| Requirement | Component | Stage | Status | Note |
|-------------|-----------|-------|--------|------|
| Authentication | Auth Service | 1 | Covered | Lock JWT vs session before code |
| Document Upload | Document Intelligence | 1 | Covered | Storage adapter required |
| PDF / CSV / Excel | Document Intelligence | 1 | Covered | Async parse jobs |
| Chunking + Embeddings + RAG | Document + Chat | 1 | Covered | Provider via adapters |
| Domain Detection + KPI Discovery | KPI Intelligence | 1 | Covered | Make domain detection explicit |
| KPI Dashboard | KPI + UI | 1 | Covered | Executive DI widgets in Stage 2 |
| AI Chat + citations | Chat (RAG) | 1 | Covered | Citation schema in API |
| Decision Cards / Summary / Health | Decision Intelligence | 2 | Deferred | Correct staging |
| Forecast + PDF Export | Forecasting + Reporting | 2 | Deferred | Correct staging |
| Audit Logging | Cross-cutting | 1 (minimal) | Gap | Add minimal audit in Stage 1 |
| Multi-tenancy / ERP / KG | — | Post-MVP | Out of scope | Keep domain extensibility |

---

## Validated Pipelines

**Stage 1 — AI Pipeline**

```
Upload → Parse → Markdown → Chunk → Embed → Qdrant → Retrieve
  → Domain Detect → KPI Extract → Dashboard → Chat (RAG)
```

**Stage 2 — Decision Pipeline (not in Stage 1)**

```
KPI → Trend → Root Cause → Risks → Opportunities
  → Recommendation → Forecast → Decision Card → Export
```

---

## Clean Architecture Layers

| Layer | Responsibility |
|-------|----------------|
| Presentation | Next.js App Router, clients, executive screens |
| Interface (API) | FastAPI routers, DTOs, OpenAPI, auth middleware |
| Application | Use cases: UploadDocument, ProcessDocument, DiscoverKPIs, AskChat |
| Domain | Document, Chunk, KPI, Citation, DomainDetection |
| Infrastructure | Postgres, Qdrant, Redis, parsers, LLM/embedding adapters, storage |

---

## Proposed Stage 1 API Surface

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/register` | Create user |
| POST | `/auth/login` | Issue tokens |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/documents/upload` | Upload PDF/CSV/XLSX |
| GET | `/documents` | List documents |
| GET | `/documents/{id}` | Status + metadata |
| POST | `/documents/{id}/process` | Trigger AI pipeline |
| GET | `/kpis` | Discovered KPIs |
| GET | `/dashboard` | Dashboard payload |
| POST | `/chat` | RAG Q&A with citations |
| GET | `/chat/sessions` | Chat history |

---

## Blocking Decisions (approve before code)

| ID | Decision | Recommendation | Blocking |
|----|----------|----------------|----------|
| D1 | Auth mechanism | JWT access + refresh; Redis for refresh/blacklist | Yes |
| D2 | LLM + embeddings | OpenAI-compatible API via env; swappable adapters | Yes |
| D3 | Document storage | Local Docker volume for MVP; S3-compatible interface | Yes |
| D4 | Async processing | Redis queue + background worker for parse/chunk/embed | Yes |
| D5 | Monorepo layout | `apps/web`, `apps/api`, `docs`, `docker-compose` | No |
| D6 | Audit logging | Minimal events for auth, upload, chat in Stage 1 | No |

---

## Risks & Mitigations

1. **Long-running document jobs** — Use async status (`processing` → `ready`/`failed`), never block HTTP on full pipeline.
2. **KPI hallucination** — Every KPI must carry evidence chunk IDs; reject uncited extractions.
3. **Thin architecture source doc** — This validation + Stage 1 design become the binding baseline.
4. **Audit gap** — Include minimal audit events in Stage 1 to avoid retrofit.

---

## Stage 1 Acceptance Criteria

User can upload PDF/CSV/Excel; system produces discovered KPIs, a dashboard payload, and citation-backed chat — with unit/integration tests, logging, and OpenAPI. **No** Decision Cards, Health Score, Forecast, or PDF Export in Stage 1.

---

## Approval Gate

Reply with:

1. Approval or overrides for **D1–D4**
2. Explicit: **Proceed with Stage 1**

Until then: **code freeze**.
