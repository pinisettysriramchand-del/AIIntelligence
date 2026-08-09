# Stage 4E Verification — Processing jobs / idempotency / retries / DLQ

**Status:** COMPLETE  
**Date:** 2026-08-09

## Scope
Part 4 §20 Reliability: durable processing jobs, idempotent reprocess, ARQ retries, dead-letter handling.

## Files changed
- `alembic/versions/006_processing_jobs.py`
- `domain/enums.py` (`ProcessingJobStatus`), `domain/entities.py` (`ProcessingJob`)
- `infrastructure/db/models.py`, `repositories.py` (jobs + `delete_by_document`)
- `application/documents.py`, `application/processing.py`
- `infrastructure/queue/tasks.py`, `worker.py`
- `config.py` (`processing_max_tries`, retry defer, DLQ key)
- documents schemas/router (job APIs)
- tests + docs

## Features
- `processing_jobs` table with status/attempt/idempotency/arq ids
- Idempotent enqueue while job is `queued`/`running`
- Idempotent reprocess: purge KPIs/chunks/vectors before rebuild
- ARQ retries via `Retry` until `processing_max_tries`
- Final failure → Postgres `dead_letter` + Redis list DLQ
- APIs: `POST .../process` → job; `GET .../jobs`; `GET /documents/jobs/{id}`; `GET /documents/jobs/dead-letter`

## Apply migration
```
cd apps\api
uv run alembic upgrade head   # -> 006_processing_jobs
```

## Limitations
- DLQ is inspectable (Postgres + Redis list); no auto-replay UI/API yet
- Decision cards are not auto-cleared on document reprocess
- Health checks / graceful degradation beyond existing `/health` deferred
