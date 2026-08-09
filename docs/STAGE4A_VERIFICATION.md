# Stage 4A Verification — Schema Truth (Decision Intelligence tables)

**Status:** COMPLETE (unit-verified; live Postgres upgrade pending local DB)  
**Date:** 2026-08-09

## Scope
Alembic migration for ORM tables that existed in code but not in `001_initial`.

## Files changed
- `apps/api/alembic/versions/002_decision_intelligence.py` (added)
- `apps/api/alembic.ini` (`path_separator=os`)
- `apps/api/tests/unit/test_migration_di.py` (added)
- `docs/PART4_ARCHITECTURE_VALIDATION.md` (updated)
- `docs/STAGE4A_VERIFICATION.md` (this file)

## Features implemented
- Create `decision_cards` with FKs to users/kpis/documents + indexes
- Create `executive_reports` with FKs to users/documents + indexes
- Downgrade drops both tables/indexes in reverse order
- Alembic head: `002_decision_intelligence`

## Tests executed
```
uv run pytest tests/unit/test_migration_di.py -q  → 5 passed
uv run pytest -q                                 → 72 passed
uv run alembic heads                             → 002_decision_intelligence (head)
uv run alembic history                           → 001_initial → 002_decision_intelligence
```

Live `alembic upgrade head` against localhost Postgres: **verified** via portable Postgres (Docker blocked by missing WSL2). See `docs/POSTGRES_LIVE_UPGRADE_FIX.md`.

Evidence:
- upgrade `-> 001_initial -> 002_decision_intelligence`
- downgrade `002 -> 001_initial`
- re-upgrade to `002_decision_intelligence (head)`

## Known limitations
- Live upgrade/downgrade against Postgres not verified in this session
- Does not add Part 4 fields (`topic`, `expected_outcome`) — Stage 4D
- Does not introduce orgs / processing_jobs — later stages

## Follow-up
- Approve Stage 4B (KPI Intelligence) or 4B+4C
- Optional: request git commit of 4A
- When Postgres is up: `alembic upgrade head` then `alembic downgrade 001_initial` smoke check
