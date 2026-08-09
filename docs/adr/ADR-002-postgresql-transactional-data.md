# ADR-002: PostgreSQL for Transactional Data

**Status:** Accepted  
**Date:** 2026-08-09  
**Part 3 ref:** Architecture §17

## Context

Users, documents, chunks metadata, KPIs, decision cards, chat sessions, and audit events require durable, relational storage with migrations and strong consistency for auth and processing status.

## Decision

Use **PostgreSQL** (async via `asyncpg` + SQLAlchemy 2.x) as the system of record. Schema changes go through **Alembic**.

## Alternatives considered

| Option | Why not |
|--------|---------|
| SQLite only | Fine for unit tests; not suitable for concurrent prod workers |
| MongoDB | Weaker relational integrity for users ↔ docs ↔ KPIs ↔ decisions |
| DynamoDB / document DB | Operational complexity; poor fit for ad-hoc joins and audit queries |

## Consequences

- Clear ownership of transactional state vs vectors (Qdrant) and blobs (local/object storage).
- Integration tests can use SQLite/aiosqlite; runtime default remains Postgres.
- Operators must run migrations before API/worker in Compose (`migrate` service).
