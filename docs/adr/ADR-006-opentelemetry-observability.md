# ADR-006: OpenTelemetry for Distributed Observability

**Status:** Accepted  
**Date:** 2026-08-09  
**Part 3 ref:** Architecture §16

## Context

Part 3 requires API latency, processing duration, AI latency, token usage, retrieval quality, error rates, and failed documents. Process-local `/metrics` is useful for MVP debugging but does not aggregate across API replicas or workers.

## Decision

Adopt **OpenTelemetry** (OTLP HTTP) as the export path:

- Disabled by default (`OTEL_ENABLED=false`)
- When enabled, instrument FastAPI + httpx and dual-write domain metrics (AI, processing, retrieval)
- Export to `OTEL_EXPORTER_OTLP_ENDPOINT` (e.g. `http://localhost:4318`)
- Keep `GET /metrics` as a process-local snapshot for operators

Optional Compose profile: `docker compose --profile otel up` runs a collector with debug exporter.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Prometheus-only scrape | Weaker distributed tracing story for RAG/LLM calls |
| Vendor agent only | Couples MVP to one SaaS; OTLP stays portable |
| Full APM suite now | Heavier than needed for Part 3 hardening |

## Consequences

- Multi-replica aggregation requires a collector/backend (Jaeger, Grafana Tempo, etc.).
- Enabling OTEL without an endpoint still initializes providers (no export) so instrumentation is safe.
- Sampling via `OTEL_TRACES_SAMPLER_RATIO` controls trace volume.
