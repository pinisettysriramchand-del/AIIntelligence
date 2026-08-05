# Stage 1 Design — Analytical MVP

**Status:** ACCEPTED (2026-08-05)  
**Approved decisions:** D1 JWT+Redis · D2 OpenAI-compatible adapters · D3 Local volume + storage port · D4 Redis worker queue · D5 Monorepo · D6 Minimal audit

## Goal

Upload PDF/CSV/Excel → parse → chunk → embed → Qdrant → domain detect → KPI discovery → dashboard → citation-backed chat.

## Out of scope (Stage 2)

Decision Cards, Executive Summary, Business Health Score, Decision Timeline, Root Cause, Risk/Opportunity narrative cards, Forecast, PDF Export.

## Repository layout

```
apps/api/     FastAPI Clean Architecture + ARQ worker
apps/web/     Next.js App Router executive UI
docs/         Product + stage design docs
docker-compose.yml
```

## Backend layers

| Layer | Package | Role |
|-------|---------|------|
| Interface | `stratiq.interface` | HTTP routers, Pydantic schemas, DI wiring |
| Application | `stratiq.application` | Use cases; depends on ports only |
| Domain | `stratiq.domain` | Entities, enums, domain errors |
| Infrastructure | `stratiq.infrastructure` | SQLAlchemy, Qdrant, Redis, parsers, LLM, storage |

## Processing flow

1. `POST /documents/upload` stores bytes via `ObjectStorage` port; row status=`uploaded`.
2. `POST /documents/{id}/process` enqueues ARQ job; status=`processing`.
3. Worker: parse → markdown → chunk → embed → upsert Qdrant → domain detect → KPI extract (each KPI requires evidence chunk IDs) → status=`ready` or `failed`.
4. `GET /dashboard` and `GET /kpis` read Postgres.
5. `POST /chat` embeds query, retrieves top-k from Qdrant, LLM answers with citations.

## Auth

- Register/login with bcrypt password hashes.
- Access JWT (short TTL) + refresh token stored hashed in Redis.
- Logout blacklists access JTI and deletes refresh key.

## Data model (Postgres)

`users`, `documents`, `chunks`, `kpis`, `chat_sessions`, `chat_messages`, `audit_events`

## API contracts (Stage 1)

Auth: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`  
Documents: `/documents/upload`, `/documents`, `/documents/{id}`, `/documents/{id}/process`  
KPIs: `/kpis`  
Dashboard: `/dashboard`  
Chat: `/chat/sessions`, `/chat/sessions/{id}/messages`, `/chat`

## Frontend screens

Login · Upload · Dashboard (KPI grid) · Chat — per UI guidelines (executive, responsive). No Decision Card UI in Stage 1.

## Test strategy

- Unit: parsers, chunker, JWT, KPI evidence validation
- Integration: auth flow, upload+status, dashboard/chat with fakes for LLM/Qdrant where needed
- Verify: `pytest` green; OpenAPI available at `/docs`
