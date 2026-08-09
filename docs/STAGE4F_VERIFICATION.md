# Stage 4F Verification — Correlation IDs

**Status:** COMPLETE  
**Date:** 2026-08-09

## Scope
Part 4 §22: correlate requests, processing jobs, and AI calls via a shared request/job identifier (OTEL attributes + logs).

## Files changed
- `infrastructure/observability/correlation.py`
- `alembic/versions/007_correlation_ids.py`
- ORM/entity/repo/schema for `processing_jobs.correlation_id`
- `interface/app_factory.py` (`CorrelationIdMiddleware`, CORS expose)
- `application/documents.py` (persist + enqueue correlation)
- `infrastructure/queue/tasks.py` (worker bind + span)
- `infrastructure/ai/llm.py` (AI span attrs)
- `infrastructure/observability/otel.py` (metric attributes)
- tests + docs

## Features
- Accept/generate `X-Request-ID` (alias `X-Correlation-ID`); echo on responses
- Contextvars + log filter (`correlation_id`, `job_id`)
- Persist `correlation_id` on processing jobs; pass through ARQ kwargs
- Worker binds correlation and opens `stratiq.process_document` span
- LLM opens `stratiq.ai.chat_completion` span with correlation attributes
- OTEL metric record/add includes correlation attributes when enabled

## Apply migration
```
cd apps\api
uv run alembic upgrade head   # -> 007_correlation_ids
```

## Limitations
- Browser clients must send/read `X-Request-ID` (exposed via CORS)
- Full distributed trace continuity across Redis queue relies on explicit correlation attribute (not W3C traceparent yet)
