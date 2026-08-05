# Stage 2 Design — Decision Intelligence

**Status:** ACCEPTED (2026-08-05)
**Depends on:** Stage 1 (accepted)

## Goal

Turn discovered KPIs into executive-ready Decision Intelligence: cards, health score, timeline, forecasts, and PDF export.

## Pipeline

```
KPI → Trend → Root Cause → Risks → Opportunities → Recommendation → Forecast → Decision Card
Aggregate → Executive Summary + Business Health Score + Decision Timeline → PDF Export
```

## APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/decisions/generate` | Generate/refresh DI for owner (optional `document_id`) |
| GET | `/api/decisions/cards` | List decision cards |
| GET | `/api/decisions/cards/{id}` | Single card |
| GET | `/api/decisions/executive` | Summary + health + timeline |
| GET | `/api/forecasts` | KPI forecasts |
| GET | `/api/reports/executive.pdf` | Download executive PDF |

## Persistence

- `decision_cards` — per KPI narrative + risks/opportunities/recommendation/forecast
- `executive_reports` — cached summary, health score, timeline JSON
- Generated after Stage 1 KPIs exist; also triggered automatically at end of document processing

## Rules

- Every card must reference the source KPI and evidence chunk IDs
- LLM outputs validated; invalid items skipped with logging
- Health score: 0–100 with label (`critical` / `watch` / `healthy`)
- PDF export is deterministic from stored DI (no live LLM call)

## UI

- Dashboard: health, executive summary snippet, timeline, top cards
- Decision Card detail page
- Reports page with PDF download

## Out of scope

Multi-tenancy, ERP connectors, knowledge graph, multi-agent orchestration.
