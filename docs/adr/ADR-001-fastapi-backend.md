# ADR-001: FastAPI Backend

**Status:** Accepted  
**Date:** 2026-08-09  
**Part 3 ref:** Architecture §17

## Context

StratIQ needs an API-first backend for auth, document intake, KPI/DI workflows, chat, and exports. The team wants typed Python, async I/O for LLM/vector/DB calls, and OpenAPI for the Next.js client.

## Decision

Use **FastAPI** as the HTTP framework, with Clean Architecture packages under `apps/api/src/stratiq` (`domain` / `application` / `infrastructure` / `interface`).

## Alternatives considered

| Option | Why not |
|--------|---------|
| Django / DRF | Heavier ORM-centric stack; weaker fit for async RAG/worker patterns |
| Flask | Less first-class OpenAPI/async; more boilerplate for validation |
| NestJS / Node | Would split language from Python ML/data parsing ecosystem |

## Consequences

- OpenAPI docs and Pydantic schemas stay aligned with routes.
- Async SQLAlchemy, Redis, Qdrant, and ARQ workers integrate naturally.
- Team must keep domain free of FastAPI imports (ports/adapters).
