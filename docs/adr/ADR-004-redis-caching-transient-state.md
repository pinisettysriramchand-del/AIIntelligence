# ADR-004: Redis for Caching and Transient State

**Status:** Accepted  
**Date:** 2026-08-09  
**Part 3 ref:** Architecture §17

## Context

Auth needs short-lived refresh tokens and access-token blacklist TTLs. Background processing needs a job broker. Some derived dashboard/DI results may be cached without becoming durable records.

## Decision

Use **Redis** for:

- Refresh-token storage and JWT blacklist TTLs
- **ARQ** worker queue / transient job state
- Optional caching of non-authoritative derived views

## Alternatives considered

| Option | Why not |
|--------|---------|
| DB-only sessions | Heavier write load; awkward TTL semantics for blacklist |
| RabbitMQ / SQS | Extra infra for MVP; ARQ+Redis is enough |
| In-memory process cache | Lost on restart; not shared across API replicas |

## Consequences

- Losing Redis invalidates refresh tokens and in-flight jobs (acceptable; users re-login / re-queue).
- Durable business data stays in PostgreSQL; Redis must not be the only copy of KPIs or decision cards.
