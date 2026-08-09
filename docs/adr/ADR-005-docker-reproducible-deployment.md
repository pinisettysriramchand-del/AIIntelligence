# ADR-005: Docker for Reproducible Deployment

**Status:** Accepted  
**Date:** 2026-08-09  
**Part 3 ref:** Architecture §17

## Context

Local and CI environments must stand up Postgres, Redis, Qdrant, API, worker, and migrations with minimal manual setup so verification is repeatable.

## Decision

Use **Docker Compose** (`docker-compose.yml`) to run infrastructure and application services with healthchecks, env files, and a dedicated `migrate` step before API start.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Manual local installs only | Drift-prone; hard for new contributors |
| Kubernetes first | Overkill for MVP verification |
| Fully managed cloud only | Blocks offline/reproducible Part 3 verification |

## Consequences

- `docker compose up` is the supported integration path for infra dependencies.
- Images must stay lean; secrets via `.env`, never committed.
- Production may later move to managed services while keeping the same service boundaries.
